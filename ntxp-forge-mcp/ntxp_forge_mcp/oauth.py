"""Google sign-in for the MCP endpoint.

MCP clients such as Claude speak OAuth 2.1 with dynamic client registration.
Google does not, so this server is the authorization server the client sees
and it sends the person to Google to prove who they are:

    client -> /authorize -> Google sign-in -> /oauth/google/callback -> client

The rule is hard coded: a verified Google Workspace account whose hosted
domain is ntxpllc.com is approved. Every other account is refused and the
refusal is written to the access log.

The state, authorization code, access token and refresh token are signed
JWTs. The server holds no session. SQLite keeps only the registered clients
and the ids of spent codes and revoked tokens.
"""
from __future__ import annotations

import json
import secrets
import time
import urllib.parse
import urllib.request
from typing import Any, Callable

import anyio
import jwt
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    RefreshToken,
    RegistrationError,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from .config import ALLOWED_DOMAIN, Settings
from .db import Store
from .policy import Denied, in_domain, normalize, role_for

GOOGLE_AUTHORIZE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")

SCOPE = "forge"
STATE_TTL = 600
CODE_TTL = 120
ACCESS_TTL = 3600
REFRESH_TTL = 30 * 24 * 3600
MIN_KEY_CHARS = 32


def identity_from_claims(claims: dict[str, Any]) -> str:
    """Return the email of an approved account, or raise Denied.

    Three checks, all required: Google verified the email, the account's
    hosted domain (`hd`) is ours, and the email itself is in our domain. A
    personal Gmail account has no `hd` claim and fails the second check.
    """
    email = normalize(claims.get("email"))
    if claims.get("email_verified") not in (True, "true"):
        raise Denied("Google has not verified this email address.", "domain_rejected")
    if normalize(claims.get("hd")) != ALLOWED_DOMAIN or not in_domain(email):
        raise Denied(f"Only {ALLOWED_DOMAIN} Google Workspace accounts can sign in.",
                     "domain_rejected")
    return email


def _exchange_with_google(settings: Settings, code: str) -> dict:
    body = urllib.parse.urlencode({
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(GOOGLE_TOKEN, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _verify_google_id_token(settings: Settings, id_token: str) -> dict:
    key = jwt.PyJWKClient(GOOGLE_JWKS).get_signing_key_from_jwt(id_token)
    return jwt.decode(id_token, key.key, algorithms=["RS256"],
                      audience=settings.google_client_id, issuer=list(GOOGLE_ISSUERS))


class GoogleGate:
    """OAuth authorization server provider backed by Google Workspace sign-in."""

    def __init__(self, settings: Settings, store: Store, *,
                 exchange: Callable[[str], dict] | None = None,
                 verify_id_token: Callable[[str], dict] | None = None):
        if len(settings.signing_key) < MIN_KEY_CHARS:
            raise ValueError(f"The signing key must be at least {MIN_KEY_CHARS} characters.")
        self.s = settings
        self.store = store
        self._exchange = exchange or (lambda code: _exchange_with_google(settings, code))
        self._verify = verify_id_token or (lambda tok: _verify_google_id_token(settings, tok))

    # -- signed tokens --------------------------------------------------------
    def _sign(self, typ: str, ttl: int, aud: str, **claims: Any) -> str:
        now = int(time.time())
        payload = {"typ": typ, "iss": self.s.public_url, "aud": aud, "iat": now,
                   "exp": now + ttl, "jti": secrets.token_urlsafe(24), **claims}
        return jwt.encode(payload, self.s.signing_key, algorithm="HS256")

    def _decode(self, token: str, typ: str, aud: str) -> dict | None:
        try:
            claims = jwt.decode(token, self.s.signing_key, algorithms=["HS256"],
                                audience=aud, issuer=self.s.public_url)
        except jwt.PyJWTError:
            return None
        return claims if claims.get("typ") == typ else None

    # -- clients --------------------------------------------------------------
    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        raw = self.store.get_client(client_id)
        return OAuthClientInformationFull.model_validate_json(raw) if raw else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        for uri in client_info.redirect_uris or []:
            parsed = urllib.parse.urlparse(str(uri))
            host = (parsed.hostname or "").lower()
            loopback = host in ("localhost", "127.0.0.1")
            if host not in self.s.redirect_hosts or (parsed.scheme != "https" and not loopback):
                self.store.log("anonymous", None, "auth", "register_client", target=str(uri),
                               outcome="denied", flag="misuse",
                               detail="redirect host is not on the allowed list")
                raise RegistrationError("invalid_redirect_uri",
                                        f"Redirect host {host!r} is not allowed.")
        self.store.save_client(client_info.client_id or "", client_info.model_dump_json())

    # -- authorize: send the person to Google ----------------------------------
    async def authorize(self, client: OAuthClientInformationFull,
                        params: AuthorizationParams) -> str:
        if params.resource and params.resource.rstrip("/") != self.s.resource_url.rstrip("/"):
            raise AuthorizeError("invalid_target", "Unknown resource.")
        state = self._sign(
            "state", STATE_TTL, self.s.public_url, cid=client.client_id,
            ru=str(params.redirect_uri), rup=params.redirect_uri_provided_explicitly,
            cc=params.code_challenge, st=params.state, sc=params.scopes or [SCOPE])
        return GOOGLE_AUTHORIZE + "?" + urllib.parse.urlencode({
            "client_id": self.s.google_client_id,
            "redirect_uri": self.s.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email",
            "state": state,
            "hd": ALLOWED_DOMAIN,          # a hint to Google; the real check is in the callback
            "access_type": "online",
            "prompt": "select_account",
        })

    async def google_callback(self, request: Request) -> Response:
        """Finish Google sign-in, apply the domain rule, return a code to the client."""
        state = self._decode(request.query_params.get("state", ""), "state", self.s.public_url)
        if not state:
            return HTMLResponse("<h1>Sign-in expired</h1><p>Start the connection again.</p>",
                                status_code=400)
        code = request.query_params.get("code")
        email = ""
        try:
            if request.query_params.get("error") or not code:
                raise Denied("Google sign-in was cancelled.", "sign_in_cancelled")
            tokens = await anyio.to_thread.run_sync(self._exchange, code)
            claims = await anyio.to_thread.run_sync(self._verify, tokens.get("id_token") or "")
            email = normalize(claims.get("email"))
            email = identity_from_claims(claims)
        except Denied as denied:
            self.store.log(email or "unknown", None, "auth", "google_sign_in",
                           outcome="denied", flag=denied.flag, detail=str(denied))
            return RedirectResponse(construct_redirect_uri(
                state["ru"], error="access_denied", error_description=str(denied),
                state=state.get("st")), status_code=302)
        except Exception as exc:  # Google unreachable, bad ID token, bad response
            self.store.log(email or "unknown", None, "auth", "google_sign_in",
                           outcome="error", detail=type(exc).__name__)
            return RedirectResponse(construct_redirect_uri(
                state["ru"], error="server_error",
                error_description="Google sign-in could not be verified.",
                state=state.get("st")), status_code=302)

        self.store.touch_user(email)
        self.store.log(email, role_for(email), "auth", "google_sign_in", target=state["cid"])
        auth_code = self._sign("code", CODE_TTL, self.s.public_url, sub=email, cid=state["cid"],
                               ru=state["ru"], rup=state["rup"], cc=state["cc"], sc=state["sc"])
        return RedirectResponse(construct_redirect_uri(
            state["ru"], code=auth_code, state=state.get("st")), status_code=302)

    # -- token endpoint -------------------------------------------------------
    async def load_authorization_code(self, client: OAuthClientInformationFull,
                                      authorization_code: str) -> AuthorizationCode | None:
        c = self._decode(authorization_code, "code", self.s.public_url)
        if not c or c["cid"] != client.client_id or self.store.is_spent(c["jti"]):
            return None
        return AuthorizationCode(
            code=authorization_code, scopes=c["sc"], expires_at=float(c["exp"]),
            client_id=c["cid"], code_challenge=c["cc"], redirect_uri=c["ru"],
            redirect_uri_provided_explicitly=c["rup"], resource=self.s.resource_url,
            subject=c["sub"])

    def _issue(self, email: str, client_id: str, scopes: list[str]) -> OAuthToken:
        if role_for(email) is None:
            raise TokenError("invalid_grant", "This account can no longer sign in.")
        access = self._sign("access", ACCESS_TTL, self.s.resource_url, sub=email,
                            cid=client_id, sc=scopes)
        refresh = self._sign("refresh", REFRESH_TTL, self.s.public_url, sub=email,
                             cid=client_id, sc=scopes)
        return OAuthToken(access_token=access, token_type="Bearer", expires_in=ACCESS_TTL,
                          scope=" ".join(scopes), refresh_token=refresh)

    async def exchange_authorization_code(self, client: OAuthClientInformationFull,
                                          authorization_code: AuthorizationCode) -> OAuthToken:
        c = self._decode(authorization_code.code, "code", self.s.public_url)
        if not c or not self.store.spend(c["jti"], c["exp"]):
            raise TokenError("invalid_grant", "The authorization code was already used.")
        return self._issue(c["sub"], c["cid"], c["sc"])

    async def load_refresh_token(self, client: OAuthClientInformationFull,
                                 refresh_token: str) -> RefreshToken | None:
        c = self._decode(refresh_token, "refresh", self.s.public_url)
        if not c or c["cid"] != client.client_id or self.store.is_spent(c["jti"]):
            return None
        return RefreshToken(token=refresh_token, client_id=c["cid"], scopes=c["sc"],
                            expires_at=int(c["exp"]), resource=self.s.resource_url,
                            subject=c["sub"])

    async def exchange_refresh_token(self, client: OAuthClientInformationFull,
                                     refresh_token: RefreshToken,
                                     scopes: list[str]) -> OAuthToken:
        c = self._decode(refresh_token.token, "refresh", self.s.public_url)
        if not c or not self.store.spend(c["jti"], c["exp"]):
            raise TokenError("invalid_grant", "The refresh token was already used.")
        return self._issue(c["sub"], c["cid"], c["sc"])

    # -- every MCP request ----------------------------------------------------
    async def load_access_token(self, token: str) -> AccessToken | None:
        c = self._decode(token, "access", self.s.resource_url)
        if not c or self.store.is_spent(c["jti"]) or role_for(c.get("sub")) is None:
            return None
        return AccessToken(token=token, client_id=c["cid"], scopes=c["sc"],
                           expires_at=int(c["exp"]), resource=self.s.resource_url,
                           subject=normalize(c["sub"]), claims={"iss": self.s.public_url})

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        for typ, aud in (("access", self.s.resource_url), ("refresh", self.s.public_url)):
            c = self._decode(token.token, typ, aud)
            if c:
                self.store.spend(c["jti"], c["exp"])
