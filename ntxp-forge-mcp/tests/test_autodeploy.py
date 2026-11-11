"""Auto deploy: live prompts, the catalog index in the instructions, autoload, the connect plugin."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import anyio
import pytest

from conftest import USER
from ntxp_forge_mcp.config import Settings
from ntxp_forge_mcp.db import Store
from ntxp_forge_mcp.forge import Forge
from ntxp_forge_mcp.server import MAX_INDEX_CHARS, build_server

PLUGIN = Path(__file__).resolve().parents[1] / "plugin" / "ntxp-forge-connect"
NEW_SKILL = "---\nname: {name}\ndescription: Skill number {name}.\n---\nBody of {name}.\n"


@pytest.fixture
def server(settings, store, forge):
    return build_server(settings, store, forge)


def prompt_names(server) -> set[str]:
    return {p.name for p in anyio.run(server.list_prompts)}


def prompt_text(server, name: str, **args) -> str:
    result = anyio.run(server.get_prompt, name, args)
    return result.messages[0].content.text


def add_skill(settings: Settings, name: str, init: dict | None = None) -> None:
    root = Path(settings.forge_local) / "skills" / name
    root.mkdir()
    (root / "SKILL.md").write_text(NEW_SKILL.format(name=name))
    if init is not None:
        (root / "mcp-init.json").write_text(json.dumps(init))


# -- one prompt per package, kept in step with Forge ---------------------------------
def test_every_package_is_a_prompt_from_the_first_request(server):
    assert prompt_names(server) == {"demo-skill", "demo-plugin"}


def test_prompt_delivers_the_skill_and_is_logged(server, store):
    text = prompt_text(server, "demo-skill", task="price the roof")
    assert "# Demo skill" in text and "Task: price the roof" in text
    assert "DEMO_REGION" in text and "Do not save it" in text
    row = store.query_log(user=USER, limit=1)[0]
    assert (row["tool"], row["action"], row["target"]) == ("prompt", "read", "skill:demo-skill")


def test_prompt_with_no_task_still_delivers_the_skill(server):
    text = prompt_text(server, "demo-skill")
    assert "# Demo skill" in text and "Task:" not in text


def test_prompt_is_refused_outside_the_domain(settings, store, forge):
    settings.dev_user = "mallory@gmail.com"
    server = build_server(settings, store, forge)
    with pytest.raises(ValueError, match="Error rendering prompt"):   # the SDK wraps the refusal
        prompt_text(server, "demo-skill")
    row = store.query_log(limit=1)[0]
    assert (row["tool"], row["outcome"], row["flag"]) == ("prompt", "denied", "not_authorized")


def test_new_forge_skill_becomes_a_prompt_with_no_reinstall(server, settings, forge):
    add_skill(settings, "added-later")
    forge._catalog = None                       # what a sync that finds a new commit does
    anyio.run(server.call_tool, "catalog_list", {})
    assert "added-later" in prompt_names(server)
    assert "- added-later (skill): Skill number added-later." in server.instructions


def test_removed_forge_skill_stops_being_a_prompt(server, settings, forge):
    import shutil
    shutil.rmtree(Path(settings.forge_local) / "plugins" / "demo-plugin")
    forge._catalog = None
    anyio.run(server.call_tool, "catalog_list", {})
    assert prompt_names(server) == {"demo-skill"}


def test_skill_and_plugin_with_one_name_get_two_prompts(settings, store, forge):
    add_skill(settings, "demo-plugin")
    assert prompt_names(build_server(settings, store, forge)) == {
        "demo-skill", "demo-plugin", "demo-plugin-plugin"}


def test_empty_forge_has_no_prompts_and_still_starts(tmp_path):
    (tmp_path / "f" / "skills").mkdir(parents=True)
    settings = Settings(data_dir=tmp_path / "d", forge_local=str(tmp_path / "f"), dev_user=USER)
    server = build_server(settings, Store(settings.db_path), Forge(settings))
    assert prompt_names(server) == set()
    assert "Live catalog (0 packages)" in server.instructions


def test_server_starts_before_any_checkout_exists(tmp_path):
    settings = Settings(data_dir=tmp_path / "d", forge_local=str(tmp_path / "missing"),
                        dev_user=USER)
    server = build_server(settings, Store(settings.db_path), Forge(settings))
    assert prompt_names(server) == set()


# -- the catalog index inside the server instructions -----------------------------------
def test_instructions_tell_the_client_to_bootstrap_and_list_the_catalog(server):
    text = server.instructions
    assert "Call `forge_bootstrap` before your first reply" in text
    assert "- demo-skill (skill): A demo skill for tests." in text
    assert "- demo-plugin (plugin): A demo plugin." in text


def test_long_catalog_index_is_cut_at_the_limit(settings, store, forge):
    for i in range(150):
        add_skill(settings, f"bulk-skill-{i:03d}")
    text = build_server(settings, store, forge).instructions
    index = text.split("when a task matches it:\n", 1)[1]
    assert len(index) <= MAX_INDEX_CHARS + 40
    assert index.rstrip().endswith("- (more: call catalog_list)")


# -- autoload: always-on packages arrive with the bootstrap ---------------------------------
def test_autoload_package_arrives_in_the_bootstrap(settings, store, forge):
    add_skill(settings, "always-on", {"autoload": True})
    add_skill(settings, "not-always", {"autoload": "yes"})     # only a real true counts
    server = build_server(settings, store, forge)
    out = anyio.run(server.call_tool, "forge_bootstrap", {}).structured_content
    assert [a["name"] for a in out["autoloaded"]] == ["always-on"]
    assert "Body of always-on." in out["autoloaded"][0]["entry"]["content"]


def test_no_autoload_packages_gives_an_empty_list(server):
    out = anyio.run(server.call_tool, "forge_bootstrap", {}).structured_content
    assert out["autoloaded"] == []


# -- the connect plugin: one install, no skill copies ----------------------------------------
def test_connect_plugin_files_are_valid():
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert manifest["name"] == "ntxp-forge-connect"
    mcp = json.loads((PLUGIN / ".mcp.json").read_text())
    assert mcp["mcpServers"]["ntxp-forge"] == {"type": "http", "url": "${NTXP_FORGE_MCP_URL}"}
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())
    assert list(hooks["hooks"]) == ["SessionStart"]


def test_connect_plugin_holds_one_router_skill_and_no_forge_content():
    skills = sorted(p.parent.name for p in PLUGIN.glob("skills/*/SKILL.md"))
    assert skills == ["ntxp-forge"]
    assert "forge_bootstrap" in (PLUGIN / "skills" / "ntxp-forge" / "SKILL.md").read_text()


def test_session_start_hook_prints_the_bootstrap_instruction():
    script = PLUGIN / "hooks" / "bin" / "session-start.sh"
    done = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0 and "call its `forge_bootstrap` tool" in done.stdout


def test_session_start_hook_fails_open_when_its_text_is_missing(tmp_path):
    script = tmp_path / "session-start.sh"
    script.write_text((PLUGIN / "hooks" / "bin" / "session-start.sh").read_text())
    done = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=5)
    assert (done.returncode, done.stdout) == (0, "")


def test_server_starts_when_the_checkout_cannot_be_read(settings, store, forge, monkeypatch):
    def unreadable():
        raise OSError("Input/output error")
    monkeypatch.setattr(forge, "catalog", unreadable)
    server = build_server(settings, store, forge)
    assert prompt_names(server) == set()
    with pytest.raises(Exception, match="could not read or write a file"):
        anyio.run(server.call_tool, "catalog_list", {})
    assert store.query_log(limit=1)[0]["outcome"] == "error"
