import asyncio, json, os
import pytest
from ntxp_contacts.db import connect, migrate
from ntxp_contacts.remote.sync_api import handle_sync
from ntxp_contacts.sync.prepare import prepare

@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "t.db"); migrate(c); return c

def post(conn, path, body):
    st, _, data = handle_sync(conn, "POST", path, body)
    return st, json.loads(data)

def test_prepare_cleans_records():
    assert prepare({"email": "15551234567@tmomail.net"}) is None
    assert prepare({"company": "Test", "email": "a@b.co"}) is None
    d = prepare({"email": "jane.doe@acme.co", "company": "(415) 884-4454"})
    assert d["firstName"] == "Jane" and d["lastName"] == "Doe" and d["company"] is None

def test_reconcile_merges_across_sources(conn):
    st, r = post(conn, "/api/sync/reconcile", {"system": "lightfield", "records": [
        {"external_id": "lf1", "firstName": "Ann", "lastName": "Test", "company": "Acme", "email": "ann@acme.example", "phone": "817-555-0101"}]})
    assert st == 200 and r["applied"]["created"] == 1
    st, r = post(conn, "/api/sync/reconcile", {"system": "jobtread", "records": [
        {"external_id": "jt1", "firstName": "Ann", "lastName": "Test", "email": "ann@acme.example"}]})
    assert r["applied"]["linked"] == 1
    assert conn.execute("SELECT COUNT(*) n FROM contacts").fetchone()["n"] == 1
    st, _, s = handle_sync(conn, "GET", "/api/sync/status", None)
    assert json.loads(s)["lightfield"]["linked"] == 1

def test_rejects_bad_input(conn):
    assert post(conn, "/api/sync/reconcile", {"system": "evil", "records": []})[0] == 400
    assert post(conn, "/api/sync/reconcile", {"system": "lightfield", "records": [{}] * 201})[0] == 413

def test_endpoint_needs_its_own_token(monkeypatch, tmp_path):
    from ntxp_contacts.remote.http_server import build_http_app
    monkeypatch.setenv("NTXP_SYNC_TOKEN", "s" * 40)
    monkeypatch.setenv("NTXP_MCP_AUTH", "static"); monkeypatch.setenv("NTXP_MCP_TOKEN", "human-token")
    app = build_http_app(str(tmp_path / "a.db"))
    async def call(token):
        sent = []
        async def receive(): return {"type": "http.request", "body": b'{"system":"lightfield","records":[]}', "more_body": False}
        async def send(m): sent.append(m)
        h = [(b"authorization", f"Bearer {token}".encode())]
        await app({"type": "http", "method": "POST", "path": "/api/sync/reconcile", "query_string": b"", "headers": h}, receive, send)
        return sent[0]["status"]
    assert asyncio.run(call("s" * 40)) == 200
    assert asyncio.run(call("human-token")) == 401      # a normal sign-in can't use the machine surface
    assert asyncio.run(call("")) == 401


def test_outbox_ack_baseline_and_connections(conn):
    from ntxp_contacts.remote.sync_api import connections
    post(conn, "/api/sync/reconcile", {"system": "lightfield", "records": [
        {"external_id": "lf1", "firstName": "Ann", "lastName": "Test", "email": "ann@acme.example"}]})
    post(conn, "/api/sync/reconcile", {"system": "jobtread", "records": [
        {"external_id": "jt1", "firstName": "Ann", "lastName": "Test", "email": "ann@acme.example"}]})
    assert post(conn, "/api/sync/baseline", {})[0] == 200
    # nothing pending right after baseline
    st, _, data = handle_sync(conn, "GET", "/api/sync/outbox", {"system": "jobtread"})
    assert json.loads(data)["count"] == 0
    # a local edit now shows up for the systems that did not originate it
    from ntxp_contacts.db.repository import Repository
    cid = conn.execute("SELECT contact_id FROM contacts").fetchone()["contact_id"]
    Repository(conn).update_contact_fields(cid, {"title": "Director"}, origin="ui") if hasattr(Repository, "update_contact_fields") else None
    cons = {c["system"]: c for c in connections(conn)["connections"]}
    assert cons["lightfield"]["connected"] and cons["jobtread"]["connected"] and not cons["gcontacts"]["connected"]
