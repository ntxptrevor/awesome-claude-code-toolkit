#!/usr/bin/env python3
"""
auth.py: Google sign-in for the MCP server, with no stored auth state.

An MCP client speaks OAuth 2.1 to this server. This server sends the person to
Google to sign in, then issues its own tokens. Every artifact of that flow is
a signed JWT that carries its own data:

    client_id       the registered redirect URIs
    state           the client's request, while the person is at Google
    auth code       who signed in, their role, and the PKCE challenge
    access token    email and role, valid 1 hour
    refresh token   email, valid 30 days

No database row is read or written. Any instance can verify any token with the
signing key alone.

Who may sign in: any verified account in PRIMARY_DOMAIN. The role is "admin"
when the email is in ADMIN_EMAILS, otherwise "reader". policy.py decides what
each role may do.

Revocation without a session table:
  * Suspend the person in Google Workspace. The next refresh (1 hour at most)
    checks the Directory and fails.
  * Remove the email from ADMIN_EMAILS. The next refresh issues a reader token.
  * Raise TOKEN_EPOCH to the current Unix time. Every token issued before that
    moment stops working, for everyone.
"""

from __future__ import annotations

import base64
import hashlib
import html
import os
import secrets
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
import jwt
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
JWT_SIGNING_KEY = os.environ.get("JWT_SIGNING_KEY", "")
PRIMARY_DOMAIN = os.environ.get("PRIMARY_DOMAIN", "").strip().lower()
ADMIN_EMAILS = {
    e.strip().lower()
    for e in os.environ.get("ADMIN_EMAILS", "").split(",")
    if e.strip()
}
TOKEN_EPOCH = int(os.environ.get("TOKEN_EPOCH", "0") or 0)

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"

ACCESS_TTL = 3600                 # 1 hour
REFRESH_TTL = 30 * 24 * 3600      # 30 days
CODE_TTL = 300                    # 5 minutes
STATE_TTL = 900                   # 15 minutes at the Google sign-in page
CLIENT_TTL = 400 * 24 * 3600      # a registered client_id lasts ~13 months
APPROVER_TTL = 600                # 10 minutes to press Approve after sign-in

ISSUER = PUBLIC_URL or "http://localhost:8080"
SCOPES = ["workspace"]

ROLE_ADMIN = "admin"
ROLE_READER = "reader"


class AuthError(Exception):
    def __init__(self, code: str, description: str, status: int = 400):
        self.code, self.description, self.status = code, description, status
        super().__init__(description)


def _key() -> str:
    if len(JWT_SIGNING_KEY) < 32:
        raise AuthError(
            "server_error",
            "JWT_SIGNING_KEY is missing or shorter than 32 characters.",
            500,
        )
    return JWT_SIGNING_KEY


# ---------------------------------------------------------------------------
# Signed-token helpers. Every token has a "typ" so one kind cannot stand in
# for another.
# ---------------------------------------------------------------------------

def sign(typ: str, ttl: int, **claims: Any) -> str:
    now = int(time.time())
    return jwt.encode(
        {"iss": ISSUER, "aud": ISSUER, "iat": now, "exp": now + ttl,
         "typ": typ, "jti": secrets.token_urlsafe(9), **claims},
        _key(),
        algorithm="HS256",
    )


def unsign(token: str, typ: str) -> Dict[str, Any]:
    try:
        claims = jwt.decode(
            token, _key(), algorithms=["HS256"], audience=ISSUER, issuer=ISSUER,
            options={"require": ["exp", "iat", "typ"]},
        )
    except jwt.ExpiredSignatureError:
        raise AuthError("invalid_token", f"The {typ} token expired.", 401)
    except jwt.InvalidTokenError as exc:
        raise AuthError("invalid_token", f"Invalid {typ} token: {exc}", 401)
    if claims.get("typ") != typ:
        raise AuthError("invalid_token", "Wrong token type.", 401)
    if claims["iat"] < TOKEN_EPOCH:
        raise AuthError("invalid_token", "This token was revoked. Sign in again.", 401)
    return claims


def role_for(email: str) -> Optional[str]:
    """The role an email address gets, or None when it may not sign in."""
    email = (email or "").strip().lower()
    if not PRIMARY_DOMAIN or "@" not in email:
        return None
    if email.rsplit("@", 1)[1] != PRIMARY_DOMAIN:
        return None
    return ROLE_ADMIN if email in ADMIN_EMAILS else ROLE_READER


def mint_access_token(email: str, role: str, client_id: str = "") -> str:
    return sign("access", ACCESS_TTL, sub=email, role=role,
                cid=hashlib.sha256(client_id.encode()).hexdigest()[:16])


def verify_access_token(token: str) -> Dict[str, Any]:
    claims = unsign(token, "access")
    # The role in the token is a cache of the configuration at issue time. An
    # admin removed from ADMIN_EMAILS loses admin rights on the next request,
    # before the 1-hour token expires.
    current = role_for(claims.get("sub", ""))
    if current is None:
        raise AuthError("invalid_token", "This account may no longer sign in.", 401)
    if claims.get("role") == ROLE_ADMIN and current != ROLE_ADMIN:
        claims["role"] = ROLE_READER
    return claims


# ---------------------------------------------------------------------------
# OAuth discovery and client registration
# ---------------------------------------------------------------------------

async def metadata(request: Request) -> JSONResponse:
    """RFC 8414 discovery: where the MCP client sends the person to sign in."""
    return JSONResponse(
        {
            "issuer": ISSUER,
            "authorization_endpoint": f"{ISSUER}/authorize",
            "token_endpoint": f"{ISSUER}/token",
            "registration_endpoint": f"{ISSUER}/register",
            "scopes_supported": SCOPES,
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
        }
    )


async def protected_resource_metadata(request: Request) -> JSONResponse:
    """RFC 9728: which authorization server guards this API."""
    return JSONResponse(
        {
            "resource": f"{ISSUER}/mcp",
            "authorization_servers": [ISSUER],
            "scopes_supported": SCOPES,
            "bearer_methods_supported": ["header"],
        }
    )


def _valid_redirect(uri: str) -> bool:
    if uri.startswith("https://"):
        return True
    return uri.startswith(("http://localhost", "http://127.0.0.1"))


async def register(request: Request) -> JSONResponse:
    """Dynamic client registration (RFC 7591), with nothing stored.

    The client_id returned is a signed token that holds the redirect URIs. The
    server reads them back from the client_id itself on /authorize.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    redirect_uris: List[str] = [
        u for u in (body.get("redirect_uris") or []) if isinstance(u, str)
    ]
    if not redirect_uris or len(redirect_uris) > 10 or not all(
        _valid_redirect(u) for u in redirect_uris
    ):
        return JSONResponse(
            {"error": "invalid_redirect_uri",
             "error_description": "1 to 10 https (or localhost) redirect_uris are required."},
            status_code=400,
        )
    name = str(body.get("client_name", "mcp-client"))[:80]
    client_id = sign("client", CLIENT_TTL, redirect_uris=redirect_uris, name=name)
    return JSONResponse(
        {
            "client_id": client_id,
            "client_name": name,
            "redirect_uris": redirect_uris,
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        },
        status_code=201,
    )


# ---------------------------------------------------------------------------
# Sign-in
# ---------------------------------------------------------------------------

def _google_redirect(state: str) -> RedirectResponse:
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": f"{PUBLIC_URL}/auth/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    if PRIMARY_DOMAIN:
        params["hd"] = PRIMARY_DOMAIN   # Google shows only this domain's accounts
    return RedirectResponse(GOOGLE_AUTH + "?" + urlencode(params))


async def authorize(request: Request) -> Any:
    """Send the person to Google. The client's request rides in a signed state."""
    q = request.query_params
    client_id, redirect_uri = q.get("client_id", ""), q.get("redirect_uri", "")
    challenge = q.get("code_challenge", "")
    try:
        client = unsign(client_id, "client")
    except AuthError:
        return HTMLResponse(page("Unknown client. Remove the connector and add it again."),
                            status_code=400)
    if redirect_uri not in client.get("redirect_uris", []):
        return HTMLResponse(page("The redirect_uri does not match the registration."),
                            status_code=400)
    if not challenge or q.get("code_challenge_method", "S256") != "S256":
        return HTMLResponse(page("PKCE with S256 is required."), status_code=400)
    state = sign(
        "state", STATE_TTL, purpose="mcp",
        cid=hashlib.sha256(client_id.encode()).hexdigest(),
        redirect_uri=redirect_uri, state=q.get("state", ""), challenge=challenge,
    )
    return _google_redirect(state)


def start_approver_sign_in(request_token: str) -> RedirectResponse:
    """Send an approver to Google before the approval page is shown."""
    return _google_redirect(sign("state", STATE_TTL, purpose="approve", rt=request_token))


async def _google_identity(code: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        tok = await client.post(
            GOOGLE_TOKEN,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": f"{PUBLIC_URL}/auth/callback",
                "grant_type": "authorization_code",
            },
        )
        if tok.status_code != 200:
            raise AuthError("access_denied", "Google rejected the sign-in code.")
        info = await client.get(
            GOOGLE_USERINFO,
            headers={"Authorization": f"Bearer {tok.json()['access_token']}"},
        )
    if info.status_code != 200:
        raise AuthError("access_denied", "Google did not return a profile.")
    return info.json()


async def callback(request: Request) -> Any:
    """Google returns here. Check the person, then continue the flow in `state`."""
    q = request.query_params
    if q.get("error"):
        return HTMLResponse(page("Google sign-in was cancelled or failed."), status_code=400)
    try:
        st = unsign(q.get("state", ""), "state")
        info = await _google_identity(q.get("code", ""))
    except AuthError as exc:
        return HTMLResponse(page(html.escape(exc.description)), status_code=400)

    email = (info.get("email") or "").lower()
    role = role_for(email)
    if (
        role is None
        or info.get("email_verified") is not True
        or (info.get("hd") or "").lower() != PRIMARY_DOMAIN
    ):
        return HTMLResponse(
            page(f"<strong>{html.escape(email or 'This account')}</strong> is not a "
                 f"verified {html.escape(PRIMARY_DOMAIN)} account. Sign in with your "
                 "company Google account."),
            status_code=403,
        )

    if st.get("purpose") == "approve":
        import policy
        return await policy.approval_page(st["rt"], email, role)

    code = sign("code", CODE_TTL, sub=email, role=role, cid=st["cid"],
                redirect_uri=st["redirect_uri"], challenge=st["challenge"])
    params = {"code": code}
    if st.get("state"):
        params["state"] = st["state"]
    sep = "&" if "?" in st["redirect_uri"] else "?"
    return RedirectResponse(f"{st['redirect_uri']}{sep}{urlencode(params)}")


# ---------------------------------------------------------------------------
# Token endpoint
# ---------------------------------------------------------------------------

def _oauth_error(code: str, description: str) -> JSONResponse:
    return JSONResponse({"error": code, "error_description": description}, status_code=400)


def _token_response(email: str, role: str, client_id: str, refresh: str) -> JSONResponse:
    return JSONResponse(
        {
            "access_token": mint_access_token(email, role, client_id),
            "token_type": "Bearer",
            "expires_in": ACCESS_TTL,
            "refresh_token": refresh,
            "scope": " ".join(SCOPES),
        },
        headers={"Cache-Control": "no-store"},
    )


async def _still_active(email: str) -> bool:
    """Ask the Directory whether the account exists and is not suspended."""
    import workspace
    try:
        user = await workspace.get_directory_user(email)
    except Exception as exc:  # noqa: BLE001
        # A deleted account must fail. A Google outage must not sign everyone out.
        return "404" not in str(exc) and "notFound" not in str(exc)
    return not user.get("suspended", False)


async def token(request: Request) -> JSONResponse:
    form = await request.form()
    grant_type = form.get("grant_type", "")
    client_id = form.get("client_id", "")
    cid = hashlib.sha256(str(client_id).encode()).hexdigest()

    if grant_type == "refresh_token":
        try:
            claims = unsign(str(form.get("refresh_token", "")), "refresh")
        except AuthError as exc:
            return _oauth_error("invalid_grant", exc.description)
        if client_id and claims.get("cid") != cid:
            return _oauth_error("invalid_grant", "This refresh token belongs to another client.")
        email = claims["sub"]
        role = role_for(email)
        if role is None or not await _still_active(email):
            return _oauth_error("invalid_grant", "This account may no longer sign in.")
        return _token_response(email, role, str(client_id), str(form.get("refresh_token")))

    if grant_type != "authorization_code":
        return _oauth_error("unsupported_grant_type", str(grant_type))

    try:
        code = unsign(str(form.get("code", "")), "code")
    except AuthError as exc:
        return _oauth_error("invalid_grant", exc.description)
    if code.get("cid") != cid:
        return _oauth_error("invalid_grant", "This code was issued to another client.")
    if form.get("redirect_uri") and form.get("redirect_uri") != code.get("redirect_uri"):
        return _oauth_error("invalid_grant", "redirect_uri mismatch.")
    # PKCE proves the caller redeeming the code is the one that asked for it.
    # It also makes a replayed code useless without the verifier.
    digest = hashlib.sha256(str(form.get("code_verifier", "")).encode()).digest()
    computed = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    if not secrets.compare_digest(computed, code.get("challenge", "")):
        return _oauth_error("invalid_grant", "PKCE check failed.")

    refresh = sign("refresh", REFRESH_TTL, sub=code["sub"], cid=cid)
    return _token_response(code["sub"], code["role"], str(client_id), refresh)


# ---------------------------------------------------------------------------
# Request gate used by server.py
# ---------------------------------------------------------------------------

def authenticate(request: Request) -> Dict[str, Any]:
    """Return the claims of a valid caller, or raise AuthError."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise AuthError("unauthorized", "Missing bearer token.", 401)
    return verify_access_token(header[7:].strip())


def unauthorized_response(exc: AuthError) -> JSONResponse:
    """A 401 names the place to sign in, as the MCP auth spec requires."""
    headers = {}
    if exc.status == 401:
        headers["WWW-Authenticate"] = (
            f'Bearer resource_metadata="{ISSUER}/.well-known/oauth-protected-resource"'
        )
    return JSONResponse(
        {"error": exc.code, "error_description": exc.description},
        status_code=exc.status,
        headers=headers,
    )


def page(message: str) -> str:
    """A small HTML page. `message` is trusted HTML; escape user data first."""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Workspace Cloud MCP</title></head>
<body style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#f3f4f6;margin:0">
<div style="max-width:520px;margin:80px auto;background:#fff;padding:36px;border-radius:10px;
box-shadow:0 1px 6px rgba(0,0,0,.1)">
<h2 style="margin:0 0 14px;color:#1a3a5c;font-size:18px">Workspace Cloud MCP</h2>
<div style="color:#374151;font-size:14px;line-height:1.65;margin:0">{message}</div>
</div></body></html>"""
