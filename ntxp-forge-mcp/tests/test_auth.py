"""Google sign-in: the domain rule, the token round trip, and the HTTP gate."""
from __future__ import annotations

import base64
import hashlib
import urllib.parse

import anyio
import pytest
from mcp.server.auth.provider import AuthorizationParams, RegistrationError, TokenError
from mcp.shared.auth import OAuthClientInformationFull
from starlette.testclient import TestClient

from conftest import ADMIN, USER
from ntxp_forge_mcp import ntxp_id
from ntxp_forge_mcp.config import Settings
from ntxp_forge_mcp.oauth import GoogleGate, identity_from_claims
from ntxp_forge_mcp.policy import Denied
from ntxp_forge_mcp.server import http_app

REDIRECT = "https://claude.ai/api/mcp/auth_callback"
VERIFIER = "v" * 50
CHALLENGE = base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).rstrip(b"=").decode()


def google(email, hd="ntxpllc.com", verified=True):
    return {"email": email, "hd": hd, "email_verified": verified}


# -- the hard-coded domain rule ----------------------------------------------------
def test_workspace_account_in_domain_is_approved():
    assert identity_from_claims(google("Alex@ntxpllc.com")) == USER


@pytest.mark.parametrize("claims", [
    google("alex@gmail.com", hd=None),                 # personal account
    google("alex@ntxpllc.com", hd=None),               # address in domain, no Workspace hd
    google("alex@other.com", hd="ntxpllc.com"),        # hd without a matching address
    google("alex@ntxpllc.com", hd="other.com"),
    google("alex@ntxpllc.com", verified=False),
    google("alex@ntxpllc.com.evil.com", hd="ntxpllc.com.evil.com"),
    google("", hd="ntxpllc.com"),                      # empty email
    {},                                                # no claims at all
])
def test_every_other_account_is_refused(claims):
    with pytest.raises(Denied):
        identity_from_claims(claims)


# -- provider round trip ---------------------------------------------------------------
def make_gate(settings, store, claims):
    return GoogleGate(settings, store, exchange=lambda code: {"id_token": "t"},
                      verify_id_token=lambda tok: claims)


def client_info(redirect=REDIRECT):
    return OAuthClientInformationFull(client_id="c1", redirect_uris=[redirect],
                                      token_endpoint_auth_method="none")


class FakeRequest:
    def __init__(self, **params):
        self.query_params = params


def sign_in(gate, client):
    """Run authorize + the Google callback. Returns the redirect back to the client."""
    async def flow():
        await gate.register_client(client)
        url = await gate.authorize(client, AuthorizationParams(
            state="s1", scopes=None, code_challenge=CHALLENGE, redirect_uri=REDIRECT,
            redirect_uri_provided_explicitly=True, resource=gate.s.resource_url))
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        assert q["hd"] == ["ntxpllc.com"] and url.startswith("https://accounts.google.com/")
        resp = await gate.google_callback(FakeRequest(state=q["state"][0], code="g"))
        return urllib.parse.parse_qs(urllib.parse.urlparse(resp.headers["location"]).query)
    return anyio.run(flow)


def test_sign_in_issues_a_token_bound_to_the_user(settings, store):
    gate, client = make_gate(settings, store, google(USER)), client_info()
    back = sign_in(gate, client)
    assert back["state"] == ["s1"]

    async def redeem():
        code = await gate.load_authorization_code(client, back["code"][0])
        assert code.subject == USER and code.code_challenge == CHALLENGE
        tokens = await gate.exchange_authorization_code(client, code)
        with pytest.raises(TokenError):                       # a code works once
            await gate.exchange_authorization_code(client, code)
        access = await gate.load_access_token(tokens.access_token)
        assert access.subject == USER and access.resource == settings.resource_url
        assert await gate.load_access_token(tokens.refresh_token) is None
        refresh = await gate.load_refresh_token(client, tokens.refresh_token)
        rotated = await gate.exchange_refresh_token(client, refresh, [])
        assert await gate.load_refresh_token(client, tokens.refresh_token) is None
        await gate.revoke_token(await gate.load_access_token(rotated.access_token))
        assert await gate.load_access_token(rotated.access_token) is None
    anyio.run(redeem)
    assert store.query_log(action="auth")[0]["outcome"] == "ok"


def test_outside_account_gets_no_code_and_is_logged(settings, store):
    gate = make_gate(settings, store, google("mallory@gmail.com", hd=None))
    back = sign_in(gate, client_info())
    assert back["error"] == ["access_denied"] and "code" not in back
    row = store.query_log(action="auth")[0]
    assert (row["user_email"], row["outcome"], row["flag"]) == (
        "mallory@gmail.com", "denied", "domain_rejected")


def test_token_signed_with_another_key_is_refused(settings, store, tmp_path):
    other = GoogleGate(Settings(data_dir=tmp_path / "o", signing_key="z" * 40), store)
    forged = other._sign("access", 600, settings.resource_url, sub=ADMIN, cid="c1", sc=["forge"])
    gate = make_gate(settings, store, google(USER))
    assert anyio.run(gate.load_access_token, forged) is None


def test_expired_and_empty_tokens_are_refused(settings, store):
    gate = make_gate(settings, store, google(USER))
    expired = gate._sign("access", -1, settings.resource_url, sub=USER, cid="c1", sc=["forge"])
    assert anyio.run(gate.load_access_token, expired) is None
    assert anyio.run(gate.load_access_token, "") is None


def test_short_signing_key_is_refused(settings, store):
    settings.signing_key = "k" * 31
    with pytest.raises(ValueError):
        GoogleGate(settings, store)


def test_client_with_a_foreign_redirect_cannot_register(settings, store):
    gate = make_gate(settings, store, google(USER))
    with pytest.raises(RegistrationError):
        anyio.run(gate.register_client, client_info("https://evil.example/cb"))
    with pytest.raises(RegistrationError):
        anyio.run(gate.register_client, client_info("http://claude.ai/cb"))
    assert store.query_log(flagged_only=True)[0]["flag"] == "misuse"


# -- the HTTP endpoint: stateless, and closed without a token ------------------------------
@pytest.fixture
def http(settings, store, forge):
    gate = make_gate(settings, store, google(USER))
    app = http_app(settings, store, forge, gate)
    with TestClient(app, base_url="http://localhost:8765") as client:
        yield client, gate


def rpc(client, method, params=None, token=None, version="2026-07-28"):
    headers = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": version,
               "Mcp-Method": method}
    if params and "name" in params:
        headers["Mcp-Name"] = params["name"]
    if token:
        headers["Authorization"] = f"Bearer {token}"
    # A 2026-07-28 request carries its own envelope: no initialize call came before it.
    envelope = {"io.modelcontextprotocol/protocolVersion": version,
                "io.modelcontextprotocol/clientCapabilities": {}}
    return client.post("/mcp", headers=headers, json={
        "jsonrpc": "2.0", "id": 1, "method": method,
        "params": {**(params or {}), "_meta": envelope}})


def test_mcp_endpoint_needs_a_token(http):
    client, _ = http
    resp = rpc(client, "tools/list")
    assert resp.status_code == 401
    assert "resource_metadata" in resp.headers["www-authenticate"]
    assert client.get("/.well-known/oauth-authorization-server").json()[
        "registration_endpoint"].endswith("/register")
    assert client.get("/health").json()["ok"] is True


def test_one_post_with_a_token_calls_a_tool_with_no_session(http, store):
    client, gate = http
    token = gate._issue(USER, "c1", ["forge"]).access_token
    resp = rpc(client, "tools/call", {"name": "whoami", "arguments": {}}, token=token)
    assert resp.status_code == 200, resp.text
    assert "mcp-session-id" not in resp.headers
    body = resp.json()["result"]
    assert body["structuredContent"]["email"] == USER
    assert store.query_log(user=USER)[0]["tool"] == "whoami"


# -- the NTXP ID dependency at first start ----------------------------------------------------
def test_first_start_stops_and_names_ntxp_id_requests(tmp_path):
    bare = Settings(data_dir=tmp_path)
    with pytest.raises(ntxp_id.NtxpIdRequired) as stop:
        ntxp_id.require_first_run(bare)
    text = str(stop.value)
    assert text.count("NTXP ID VAULT REQUEST") == 4
    assert "NTXP_FORGE_MCP_GITHUB_TOKEN" in text and "NTXP_FORGE_MCP_SIGNING_KEY" in text
    assert ntxp_id.status(bare)["ready"] is False


def test_first_start_passes_when_credentials_are_set(settings):
    ntxp_id.require_first_run(settings)
    assert ntxp_id.status(settings)["ready"] is True
