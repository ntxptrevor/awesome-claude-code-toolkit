"""
End-to-end tests. They drive the real ASGI app over HTTP: OAuth sign-in, the
MCP endpoint, the access policy and the approval pages. Google is replaced by
fakes, so no network and no credentials are needed.

Run:  python -m pytest tests -q
"""

import base64
import hashlib
import json
import os
import re
import sys
import time
from urllib.parse import parse_qs, urlparse

import pytest

DOMAIN = "example.com"
ADMIN = f"owner@{DOMAIN}"
ALICE = f"alice@{DOMAIN}"
BOB = f"bob@{DOMAIN}"

os.environ.update(
    PUBLIC_URL="https://gwi.test",
    GOOGLE_CLIENT_ID="cid",
    GOOGLE_CLIENT_SECRET="csecret",
    JWT_SIGNING_KEY="k" * 48,
    PRIMARY_DOMAIN=DOMAIN,
    ADMIN_EMAILS=ADMIN,
    ADMIN_EMAIL=ADMIN,
)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starlette.testclient import TestClient  # noqa: E402

import auth  # noqa: E402
import policy  # noqa: E402
import server  # noqa: E402
import workspace  # noqa: E402
import workspace_write  # noqa: E402

REDIRECT = "https://client.test/cb"
MAIL = []       # (to, subject, body) captured from send_system_mail
CALLS = []      # (function, args) captured from the Google fakes


@pytest.fixture(scope="module")
def client():
    with TestClient(server.app, base_url="https://gwi.test") as c:
        yield c


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    MAIL.clear()
    CALLS.clear()

    async def mail(to, subject, body):
        MAIL.append((to, subject, body))

    def fake(name, result):
        async def fn(*args, **kwargs):
            CALLS.append((name, args))
            return result
        return fn

    async def directory_user(email):
        return {"primaryEmail": email, "suspended": email.startswith("gone")}

    monkeypatch.setattr(workspace_write, "send_system_mail", mail)
    monkeypatch.setattr(workspace, "get_directory_user", directory_user)
    monkeypatch.setattr(workspace, "gmail_search", fake("gmail_search", [{"id": "m1"}]))
    monkeypatch.setattr(workspace, "calendar_events", fake("calendar_events", []))
    monkeypatch.setattr(workspace, "directory_users", fake("directory_users", []))
    monkeypatch.setattr(workspace, "org_gmail_search", fake("org_gmail_search", []))
    monkeypatch.setattr(workspace_write, "gmail_trash", fake("gmail_trash", {"in_trash": True}))


def google_says(monkeypatch, email, verified=True, hd=DOMAIN):
    async def identity(code):
        return {"email": email, "email_verified": verified, "hd": hd}
    monkeypatch.setattr(auth, "_google_identity", identity)


def sign_in(client, monkeypatch, email):
    """The whole OAuth flow, as an MCP client performs it."""
    reg = client.post("/register", json={"redirect_uris": [REDIRECT], "client_name": "t"})
    assert reg.status_code == 201
    client_id = reg.json()["client_id"]
    verifier = "v" * 64
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    r = client.get("/authorize", params={
        "client_id": client_id, "redirect_uri": REDIRECT, "state": "xyz",
        "code_challenge": challenge, "code_challenge_method": "S256",
        "response_type": "code"}, follow_redirects=False)
    assert r.status_code == 307
    google = urlparse(r.headers["location"])
    q = parse_qs(google.query)
    assert google.netloc == "accounts.google.com" and q["hd"] == [DOMAIN]
    google_says(monkeypatch, email)
    r = client.get("/auth/callback", params={"code": "g", "state": q["state"][0]},
                   follow_redirects=False)
    assert r.status_code == 307, r.text
    back = parse_qs(urlparse(r.headers["location"]).query)
    assert back["state"] == ["xyz"]
    form = {"grant_type": "authorization_code", "code": back["code"][0],
            "client_id": client_id, "redirect_uri": REDIRECT, "code_verifier": verifier}
    tok = client.post("/token", data=form)
    assert tok.status_code == 200, tok.text
    return tok.json(), client_id, form


def rpc(client, token, method, params=None):
    r = client.post(
        "/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/json, text/event-stream",
                 "MCP-Protocol-Version": "2025-06-18"})
    assert r.status_code == 200, r.text
    return r.json()["result"]


def call(client, token, tool, **args):
    return rpc(client, token, "tools/call", {"name": tool, "arguments": args}
               )["content"][0]["text"]


def token_for(email):
    return auth.mint_access_token(email, auth.role_for(email))


# -- sign-in -----------------------------------------------------------------

def test_no_token_gets_401_with_discovery_header(client):
    r = client.post("/mcp/", json={})
    assert r.status_code == 401
    assert "oauth-protected-resource" in r.headers["www-authenticate"]


def test_discovery_documents(client):
    meta = client.get("/.well-known/oauth-authorization-server").json()
    assert meta["token_endpoint_auth_methods_supported"] == ["none"]
    assert client.get("/.well-known/oauth-protected-resource").json()["resource"].endswith("/mcp")


def test_full_sign_in_gives_roles(client, monkeypatch):
    tok, _, _ = sign_in(client, monkeypatch, ALICE)
    assert auth.verify_access_token(tok["access_token"])["role"] == "reader"
    tok, _, _ = sign_in(client, monkeypatch, ADMIN)
    assert auth.verify_access_token(tok["access_token"])["role"] == "admin"


@pytest.mark.parametrize("email,verified,hd", [
    ("mallory@evil.com", True, "evil.com"),
    (f"x@{DOMAIN}.evil.com", True, DOMAIN),     # look-alike domain
    (ALICE, False, DOMAIN),                      # unverified address
    (ALICE, True, ""),                           # personal account, no hosted domain
])
def test_outside_accounts_cannot_sign_in(client, monkeypatch, email, verified, hd):
    reg = client.post("/register", json={"redirect_uris": [REDIRECT]}).json()
    r = client.get("/authorize", params={
        "client_id": reg["client_id"], "redirect_uri": REDIRECT,
        "code_challenge": "c" * 43}, follow_redirects=False)
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    google_says(monkeypatch, email, verified, hd)
    r = client.get("/auth/callback", params={"code": "g", "state": state},
                   follow_redirects=False)
    assert r.status_code == 403


def test_pkce_and_client_binding(client, monkeypatch):
    _, client_id, form = sign_in(client, monkeypatch, ALICE)
    assert client.post("/token", data={**form, "code_verifier": "wrong"}).status_code == 400
    other = client.post("/register", json={"redirect_uris": [REDIRECT]}).json()["client_id"]
    assert client.post("/token", data={**form, "client_id": other}).status_code == 400


def test_authorize_rejects_unregistered_redirect_and_missing_pkce(client):
    reg = client.post("/register", json={"redirect_uris": [REDIRECT]}).json()
    bad = client.get("/authorize", params={
        "client_id": reg["client_id"], "redirect_uri": "https://evil.test/cb",
        "code_challenge": "c" * 43}, follow_redirects=False)
    assert bad.status_code == 400
    nopkce = client.get("/authorize", params={
        "client_id": reg["client_id"], "redirect_uri": REDIRECT}, follow_redirects=False)
    assert nopkce.status_code == 400
    assert client.post("/register", json={"redirect_uris": ["http://evil.test/cb"]}
                       ).status_code == 400


def test_refresh_rechecks_the_directory(client, monkeypatch):
    tok, client_id, _ = sign_in(client, monkeypatch, ALICE)
    form = {"grant_type": "refresh_token", "refresh_token": tok["refresh_token"],
            "client_id": client_id}
    assert client.post("/token", data=form).status_code == 200
    gone = auth.sign("refresh", 60, sub=f"gone@{DOMAIN}",
                     cid=hashlib.sha256(client_id.encode()).hexdigest())
    assert client.post("/token", data={**form, "refresh_token": gone}).status_code == 400


def test_one_token_type_cannot_stand_in_for_another(client, monkeypatch):
    tok, _, _ = sign_in(client, monkeypatch, ALICE)
    r = client.post("/mcp/", json={}, headers={"Authorization": f"Bearer {tok['refresh_token']}"})
    assert r.status_code == 401
    forged = auth.sign("grant", 60, sub=ALICE, role="admin")
    assert client.post("/mcp/", json={}, headers={"Authorization": f"Bearer {forged}"}
                       ).status_code == 401


def test_token_epoch_revokes_everything(client, monkeypatch):
    token = token_for(ALICE)
    monkeypatch.setattr(auth, "TOKEN_EPOCH", int(time.time()) + 10)
    assert client.post("/mcp/", json={}, headers={"Authorization": f"Bearer {token}"}
                       ).status_code == 401


def test_removed_admin_drops_to_reader_at_once(client, monkeypatch):
    token = token_for(ADMIN)
    monkeypatch.setattr(auth, "ADMIN_EMAILS", set())
    assert "Read-only" in call(client, token, "gmail_trash", user_email=BOB,
                               message_id="m", confirm=True)


# -- policy over MCP ---------------------------------------------------------

def test_tool_list_depends_on_role(client):
    reader = {t["name"] for t in rpc(client, token_for(ALICE), "tools/list")["tools"]}
    admin = {t["name"] for t in rpc(client, token_for(ADMIN), "tools/list")["tools"]}
    assert "gmail_search" in reader and "access_request" in reader
    assert not {n for n in reader if policy.is_write_tool(n)}
    assert {"gmail_send", "drive_trash", "directory_delete_user", "calendar_delete_event"} <= admin


def test_every_tool_has_a_rule_and_every_rule_a_tool():
    assert {t.name for t in server.TOOLS} == set(policy.RULES)


def test_reader_reads_own_data_and_directory(client):
    t = token_for(ALICE)
    assert "m1" in call(client, t, "gmail_search", user_email=ALICE)
    assert not call(client, t, "workspace_directory_users").startswith("Access")
    assert CALLS[0] == ("gmail_search", (ALICE, "", 25))


def test_reader_is_refused_other_accounts_and_org_wide(client):
    t = token_for(ALICE)
    assert call(client, t, "gmail_search", user_email=BOB).startswith("Access")
    assert call(client, t, "org_gmail_search", query="x").startswith("Access")
    assert call(client, t, "kb_sql", sql="select 1").startswith("Access")
    assert call(client, t, "workspace_activity_report").startswith("Access")
    assert call(client, t, "workspace_connection_check").startswith("Access")
    assert CALLS == []


def test_reader_cannot_write_even_with_a_grant(client):
    t = token_for(ALICE)
    grant = policy.mint_grant(ALICE, ["gmail.read"], ["*"], "t", 600, ADMIN)
    out = call(client, t, "gmail_trash", user_email=ALICE, message_id="m",
               confirm=True, grant=grant)
    assert "Read-only" in out and CALLS == []
    with pytest.raises(policy.PolicyError):
        policy._clean(["gmail.write"], ["*"])


def test_grant_scope_is_exact(client):
    t = token_for(ALICE)
    g = policy.mint_grant(ALICE, ["gmail.read"], [BOB], "t", 600, ADMIN)
    assert "m1" in call(client, t, "gmail_search", user_email=BOB, grant=g)
    assert call(client, t, "calendar_list_events", user_email=BOB, grant=g).startswith("Access")
    assert call(client, t, "gmail_search", user_email=f"carol@{DOMAIN}", grant=g
                ).startswith("Access")
    assert call(client, t, "org_gmail_search", query="x", grant=g).startswith("Access")
    # another person's grant is useless
    assert "another person" in call(client, token_for(BOB), "gmail_search",
                                    user_email=ALICE, grant=g)
    # an expired grant is useless
    old = auth.sign("grant", -5, sub=ALICE, perms=["gmail.read"], targets=["*"])
    assert call(client, t, "gmail_search", user_email=BOB, grant=old).startswith("Access")


def test_admin_writes_need_confirmation(client):
    t = token_for(ADMIN)
    assert "confirm=true" in call(client, t, "gmail_trash", user_email=BOB, message_id="m")
    assert CALLS == []
    assert "in_trash" in call(client, t, "gmail_trash", user_email=BOB, message_id="m",
                              confirm=True)
    assert "m1" in call(client, t, "gmail_search", user_email=BOB)


def test_two_callers_on_one_instance_keep_their_own_identity(client):
    a, o = token_for(ALICE), token_for(ADMIN)
    for _ in range(3):
        assert json.loads(call(client, a, "access_whoami"))["email"] == ALICE
        assert json.loads(call(client, o, "access_whoami"))["role"] == "admin"


def test_unknown_tool_is_refused(client):
    assert call(client, token_for(ADMIN), "no_such_tool").startswith("Access")


# -- task profiles and approval ---------------------------------------------

def test_request_matching_a_profile_is_granted_at_once(client):
    t = token_for(ALICE)
    out = json.loads(call(client, t, "access_request", task="schedule-coordination",
                          permissions=["calendar.read"], targets=["*"],
                          reason="Find a time for the pre-construction meeting."))
    assert out["status"] == "granted" and MAIL == []
    assert not call(client, t, "calendar_list_events", user_email=BOB,
                    grant=out["grant"]).startswith("Access")
    # the profile does not stretch to mail
    assert call(client, t, "gmail_search", user_email=BOB, grant=out["grant"]
                ).startswith("Access")


def test_request_outside_a_profile_needs_admin_approval(client, monkeypatch):
    t = token_for(ALICE)
    out = json.loads(call(client, t, "access_request", task="schedule-coordination",
                          permissions=["calendar.read", "gmail.read"], targets=[BOB],
                          reason="Trace the owner reply on the change order."))
    assert out["status"] == "pending_approval" and "grant" not in out
    to, subject, body = MAIL[0]
    assert to == ADMIN and ALICE in subject
    link = re.search(r"https://gwi\.test(/access/review\?rt=\S+)", body).group(1)

    # Opening the link approves nothing. It sends the approver to Google.
    r = client.get(link, follow_redirects=False)
    assert r.status_code == 307 and "accounts.google.com" in r.headers["location"]
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]

    # A reader who signs in cannot decide.
    google_says(monkeypatch, BOB)
    assert client.get("/auth/callback", params={"code": "g", "state": state}).status_code == 403

    google_says(monkeypatch, ADMIN)
    page = client.get("/auth/callback", params={"code": "g", "state": state})
    assert page.status_code == 200 and "Approve" in page.text and "gmail.read" in page.text
    fields = dict(re.findall(r"name='(rt|approver)' value='([^']+)'", page.text))

    # A forged approver token is refused.
    bad = client.post("/access/decide", data={**fields, "decision": "approve",
                                              "approver": token_for(ADMIN)})
    assert bad.status_code == 400 and len(MAIL) == 1

    done = client.post("/access/decide", data={**fields, "decision": "approve"})
    assert done.status_code == 200
    to, subject, body = MAIL[1]
    assert to == ALICE and "approved" in subject
    grant = body.strip().splitlines()[-1]
    assert "m1" in call(client, t, "gmail_search", user_email=BOB, grant=grant)


def test_denied_request_issues_no_grant(client, monkeypatch):
    call(client, token_for(ALICE), "access_request", task="audit", permissions=["kb.read"],
         reason="Review last month's response times.")
    link = re.search(r"(/access/review\?rt=\S+)", MAIL[0][2]).group(1)
    state = parse_qs(urlparse(
        client.get(link, follow_redirects=False).headers["location"]).query)["state"][0]
    google_says(monkeypatch, ADMIN)
    page = client.get("/auth/callback", params={"code": "g", "state": state})
    fields = dict(re.findall(r"name='(rt|approver)' value='([^']+)'", page.text))
    assert client.post("/access/decide", data={**fields, "decision": "deny"}).status_code == 200
    assert "denied" in MAIL[1][1] and "eyJ" not in MAIL[1][2]


def test_bad_requests_are_refused(client):
    t = token_for(ALICE)
    assert "cannot be granted" in call(client, t, "access_request", task="x",
                                       permissions=["drive.write"], reason="I need to edit.")
    assert "not an account" in call(client, t, "access_request", task="x",
                                    permissions=["gmail.read"], targets=["ceo@other.com"],
                                    reason="Read an outside mailbox.")
    assert "reason" in call(client, t, "access_request", task="x",
                            permissions=["gmail.read"], reason="pls")
    assert MAIL == []


# -- empty, missing and boundary inputs --------------------------------------

@pytest.mark.parametrize("email", ["", None, "no-at-sign", f"@{DOMAIN}x", f"a@sub.{DOMAIN}"])
def test_role_for_rejects_malformed_addresses(email):
    assert auth.role_for(email) is None


def test_empty_and_missing_arguments(client):
    t = token_for(ALICE)
    # a per-person tool with no account named is refused before any Google call
    assert "required" in call(client, t, "gmail_search")
    assert "required" in call(client, t, "gmail_search", user_email="")
    # no permissions, and an empty target list (which means the whole organisation)
    assert "at least one permission" in call(
        client, t, "access_request", task="x", permissions=[], reason="Empty list on purpose.")
    out = json.loads(call(client, t, "access_request", task="schedule-coordination",
                          permissions=["calendar.read"], targets=[],
                          reason="Empty targets mean every account."))
    assert out["status"] == "granted"
    # an empty grant string is the same as no grant
    assert call(client, t, "gmail_search", user_email=BOB, grant="").startswith("Access")
    assert CALLS == []


def test_grant_expiry_boundary(client):
    t = token_for(ALICE)
    # 60 seconds left: accepted. Expiring this very second: refused.
    live = auth.sign("grant", 60, sub=ALICE, perms=["gmail.read"], targets=[BOB])
    assert "m1" in call(client, t, "gmail_search", user_email=BOB, grant=live)
    at_expiry = auth.sign("grant", 0, sub=ALICE, perms=["gmail.read"], targets=[BOB])
    assert call(client, t, "gmail_search", user_email=BOB,
                grant=at_expiry).startswith("Access")


def test_grant_ttl_is_capped():
    g = policy.mint_grant(ALICE, ["gmail.read"], [BOB], "t", 10 * 24 * 3600, ADMIN)
    claims = auth.unsign(g, "grant")
    assert claims["exp"] - claims["iat"] == policy.GRANT_TTL_MAX


def test_target_list_limit():
    many = [f"u{i}@{DOMAIN}" for i in range(51)]
    with pytest.raises(policy.PolicyError):
        policy._clean(["gmail.read"], many)
    assert policy._clean(["gmail.read"], many[:50])[1] == sorted(many[:50])
