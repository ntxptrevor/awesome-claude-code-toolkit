"""Role policy, the copy guard, cross-user rules and the access log, through the tools."""
from __future__ import annotations

import sqlite3

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from conftest import ADMIN, OTHER, USER
from ntxp_forge_mcp import policy


def flags(store, user=""):
    return [r["flag"] for r in store.query_log(user=user, flagged_only=True)]


# -- roles ---------------------------------------------------------------------
def test_only_trevor_is_admin():
    assert policy.role_for("trevor@ntxpllc.com") == "admin"
    assert policy.role_for("Trevor@NTXPLLC.com ") == "admin"
    assert policy.role_for("alex@ntxpllc.com") == "user"


@pytest.mark.parametrize("email", [
    "", None, "trevor@gmail.com", "trevor@ntxpllc.com.evil.com", "a@evil-ntxpllc.com",
    "trevor@sub.ntxpllc.com", "@ntxpllc.com", "ntxpllc.com"])
def test_outside_domain_has_no_role(email):
    assert policy.role_for(email) is None


def test_no_identity_is_refused_and_logged(call, store):
    with pytest.raises(ToolError):
        call("whoami", as_user="mallory@gmail.com")
    row = store.query_log(limit=1)[0]
    assert (row["outcome"], row["flag"]) == ("denied", "not_authorized")


# -- bootstrap and live loading --------------------------------------------------
def test_bootstrap_returns_live_state(call):
    out = call("forge_bootstrap", skills=["demo-skill"])
    assert out["user"] == {"email": USER, "role": "user", "first_use": True,
                           "permissions": policy.permissions("user")}
    assert {c["name"] for c in out["catalog"]} == {"demo-skill", "demo-plugin"}
    assert out["instructions"]["CLAUDE.md"] == "Forge rules.\n"
    assert call("forge_bootstrap")["user"]["first_use"] is False


def test_skill_load_serves_entry_document(call):
    out = call("skill_load", name="demo-skill")
    assert out["entry"]["path"] == "SKILL.md" and "# Demo skill" in out["entry"]["content"]
    assert out["version"] == "1.2.3" and out["files"] == 23
    plugin = call("skill_load", name="plugin:demo-plugin")
    assert plugin["components"]["skills"] == ["inner"]


def test_env_init_never_returns_a_credential_value(call):
    out = call("env_init", names=["demo-skill", "demo-plugin"])
    assert "export DEMO_REGION=us-central" in out["shell"]
    assert "export DEMO_API_KEY" not in out["shell"]
    assert '"${DEMO_API_KEY:?' in out["shell"] and '"${DEMO_TOKEN:?' in out["shell"]
    assert "# set DEMO_MCP_URL" in out["shell"]
    blocks = {r["env"]: r["request"] for r in out["ntxp_id_requests"]}
    assert set(blocks) == {"DEMO_API_KEY", "DEMO_TOKEN"}
    assert blocks["DEMO_API_KEY"].startswith("NTXP ID VAULT REQUEST\nkey:        Demo service")
    assert f"requester:  {USER}" in blocks["DEMO_API_KEY"]
    assert out["workflows"] == [{"name": "install", "run": "pip install -r requirements.txt",
                                 "package": "demo-skill"}]


# -- default users are read only, except the three append lists -------------------
def test_user_can_append_and_read_but_not_delete_entries(call, store):
    for kind in policy.APPENDABLE_KINDS:
        call("entry_append", kind=kind, scope="demo-skill", text=f"note for {kind}")
    listed = call("entry_list", scope="demo-skill")
    assert listed["count"] == 3 and listed["entries"][0]["author_email"] == USER
    with pytest.raises(ToolError):
        call("entry_delete", entry_id=listed["entries"][0]["id"], reason="tidy up the list")
    assert call("entry_list", scope="demo-skill")["count"] == 3
    assert "write_denied" in flags(store, USER)


def test_entries_cannot_be_edited_by_anyone(call, store):
    entry_id = call("entry_append", kind="changelog", scope="forge", text="v1")["id"]
    with pytest.raises(sqlite3.DatabaseError):
        store._run("UPDATE entries SET body = 'changed' WHERE id = ?", (entry_id,))


def test_user_cannot_write_or_delete_config(call, store):
    with pytest.raises(ToolError):
        call("config_write", name="prefs", content="# mine")
    with pytest.raises(ToolError):
        call("config_delete", name="prefs")
    with pytest.raises(ToolError):
        call("forge_sync", force=True)
    assert flags(store, USER).count("write_denied") == 3


def test_entry_with_a_credential_is_refused(call, store):
    with pytest.raises(ToolError):
        call("entry_append", kind="usage_note", scope="forge",
             text="use ghp_" + "a1B2" * 10 + " for the fetch")
    assert call("entry_list")["count"] == 0
    assert "secret_in_write" in flags(store, USER)


# -- admin -------------------------------------------------------------------------
def test_admin_can_write_read_and_delete(call):
    call("config_write", as_user=ADMIN, name="prefs", content="# Trevor\n")
    assert call("config_read", as_user=ADMIN, name="prefs.md")["content"] == "# Trevor\n"
    assert call("config_list", as_user=ADMIN)["files"] == ["prefs.md"]
    call("config_delete", as_user=ADMIN, name="prefs")
    assert call("config_list", as_user=ADMIN)["files"] == []
    entry_id = call("entry_append", as_user=USER, kind="activity", scope="forge", text="x")["id"]
    call("entry_delete", as_user=ADMIN, entry_id=entry_id, reason="posted to the wrong list")
    assert call("entry_list")["count"] == 0


# -- whole-package copies ------------------------------------------------------------
def test_export_is_owner_only_and_the_attempt_is_logged(call, store):
    with pytest.raises(ToolError):
        call("package_export", name="demo-skill", reason="I want a local copy")
    row = store.query_log(user=USER, flagged_only=True)[0]
    assert (row["action"], row["outcome"], row["flag"]) == ("copy", "denied", "copy_attempt")
    out = call("package_export", as_user=ADMIN, name="demo-skill", reason="audit of the package")
    assert out["files"] == 23 and out["format"] == "tar.gz"
    assert store.query_log(user=ADMIN, action="copy")[0]["flag"] == "package_export"


def test_reading_file_after_file_trips_the_copy_guard(call, store, settings):
    for i in range(settings.copy_max_per_package):
        call("package_file", name="demo-skill", path=f"references/ref{i:02d}.md")
    call("package_file", name="demo-skill", path="references/ref00.md")  # a re-read is free
    with pytest.raises(ToolError):
        call("package_file", name="demo-skill", path="references/ref19.md")
    row = store.query_log(user=USER, flagged_only=True)[0]
    assert (row["action"], row["flag"]) == ("copy", "copy_suspected")
    # the owner has no limit
    for i in range(20):
        call("package_file", as_user=ADMIN, name="demo-skill", path=f"references/ref{i:02d}.md")


@pytest.mark.parametrize("name,path", [
    ("demo-skill", "../../outside.txt"), ("demo-skill", "/etc/passwd"),
    ("../..", "outside.txt"), ("demo-skill/../..", "outside.txt")])
def test_path_escape_is_refused_and_logged_as_misuse(call, store, name, path):
    with pytest.raises(ToolError):
        call("package_file", name=name, path=path)
    assert flags(store, USER) == ["misuse"]


# -- other users' information ------------------------------------------------------------
def test_user_cannot_read_another_users_records(call, store):
    call("config_write", as_user=ADMIN, name="prefs", content="# Sam\n", user=OTHER,
         reason="initial setup for Sam")
    for tool, args in [("config_read", {"name": "prefs", "user": OTHER}),
                       ("config_list", {"user": OTHER}),
                       ("access_log", {"user": OTHER}),
                       ("access_log", {"user": "*"})]:
        with pytest.raises(ToolError):
            call(tool, **args, reason="I am curious about this person")
    assert flags(store, USER) == ["cross_user"] * 4
    assert call("config_read", as_user=OTHER, name="prefs")["content"] == "# Sam\n"


def test_admin_needs_a_reason_for_another_users_records(call, store):
    call("whoami", as_user=USER)
    with pytest.raises(ToolError):
        call("access_log", as_user=ADMIN, user=USER)
    assert flags(store, ADMIN) == ["cross_user_no_reason"]
    out = call("access_log", as_user=ADMIN, user=USER, reason="checking a reported copy attempt")
    assert out["count"] == 1 and out["rows"][0]["tool"] == "whoami"
    row = store.query_log(user=ADMIN, limit=1)[0]
    assert (row["flag"], row["reason"]) == ("cross_user", "checking a reported copy attempt")


# -- the access log itself ------------------------------------------------------------------
def test_every_call_is_logged_with_user_date_and_time(call, store):
    call("skill_load", name="demo-skill")
    call("entry_append", kind="activity", scope="demo-skill", text="ran it")
    rows = call("access_log")["rows"]
    assert [(r["tool"], r["action"], r["outcome"]) for r in rows] == [
        ("entry_append", "write", "ok"), ("skill_load", "read", "ok")]
    r = rows[0]
    assert r["user_email"] == USER and r["ts_utc"].startswith(r["date_stamp"])
    assert len(r["date_stamp"]) == 10 and len(r["time_stamp"]) == 8


def test_access_log_rows_cannot_be_changed_or_deleted(call, store):
    call("whoami")
    for sql in ("DELETE FROM access_log", "UPDATE access_log SET user_email = 'x'"):
        with pytest.raises(sqlite3.DatabaseError):
            store._run(sql)
    assert len(store.query_log()) == 1


def test_parallel_reads_cannot_pass_the_copy_limit(settings, store, forge):
    from concurrent.futures import ThreadPoolExecutor

    import anyio

    from ntxp_forge_mcp.server import build_server
    server = build_server(settings, store, forge)   # one server, as in production

    def read(i):
        try:
            anyio.run(server.call_tool, "package_file",
                      {"name": "demo-skill", "path": f"references/ref{i:02d}.md"})
            return True
        except ToolError:
            return False
    with ThreadPoolExecutor(max_workers=20) as pool:
        served = sum(pool.map(read, range(20)))
    assert served == settings.copy_max_per_package


@pytest.mark.parametrize("metadata", ["1", "[]", "text", "null"])
def test_malformed_metadata_does_not_break_the_catalog(call, settings, metadata):
    from pathlib import Path
    bad = Path(settings.forge_local) / "skills" / "bad-meta"
    bad.mkdir()
    (bad / "SKILL.md").write_text(f"---\nname: bad-meta\nmetadata: {metadata}\n---\nBody.\n")
    items = {c["name"]: c for c in call("catalog_list")["items"]}
    assert items["bad-meta"]["version"] == ""


def test_write_is_rolled_back_when_its_log_row_cannot_be_saved(call, store, monkeypatch):
    real_log = store.log

    def failing_log(*args, **kwargs):
        if kwargs.get("outcome", "ok") == "ok":
            raise sqlite3.OperationalError("disk is full")
        return real_log(*args, **kwargs)
    monkeypatch.setattr(store, "log", failing_log)
    with pytest.raises(ToolError):
        call("entry_append", kind="activity", scope="forge", text="must not be saved")
    monkeypatch.setattr(store, "log", real_log)
    assert call("entry_list")["count"] == 0
    assert store.query_log(user=USER, action="write")[0]["outcome"] == "error"


def test_database_failure_on_a_read_is_reported_not_raised_raw(call, store, monkeypatch):
    def broken(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")
    monkeypatch.setattr(store, "list_entries", broken)
    with pytest.raises(ToolError, match="server database"):
        call("entry_list")
