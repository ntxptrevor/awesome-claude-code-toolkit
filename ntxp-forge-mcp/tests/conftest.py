"""Shared fixtures: a small fake NTXP Forge checkout and a server built on it."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ntxp_forge_mcp.config import Settings
from ntxp_forge_mcp.db import Store
from ntxp_forge_mcp.forge import Forge
from ntxp_forge_mcp.server import build_server

ADMIN = "trevor@ntxpllc.com"
USER = "alex@ntxpllc.com"
OTHER = "sam@ntxpllc.com"

SKILL_MD = """---
name: demo-skill
description: A demo skill for tests.
metadata:
  version: 1.2.3
requires:
  connectors:
  - google-sheets
---

# Demo skill

Follow these steps.
"""


def make_forge(root: Path) -> Path:
    skill = root / "skills" / "demo-skill"
    (skill / "references").mkdir(parents=True)
    (skill / "scripts").mkdir()
    (skill / "SKILL.md").write_text(SKILL_MD)
    for i in range(20):
        (skill / "references" / f"ref{i:02d}.md").write_text(f"reference {i}\n")
    (skill / "scripts" / "run.py").write_text("print('hi')\n")
    (skill / "mcp-init.json").write_text(json.dumps({
        "env": {"DEMO_REGION": {"value": "us-central"},
                "DEMO_API_KEY": {"vault_title": "Demo service"}},
        "workflows": [{"name": "install", "run": "pip install -r requirements.txt"}],
    }))
    plugin = root / "plugins" / "demo-plugin"
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / "skills" / "inner").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps(
        {"name": "demo-plugin", "version": "0.9.0", "description": "A demo plugin."}))
    (plugin / "skills" / "inner" / "SKILL.md").write_text("---\nname: inner\n---\nInner.\n")
    (plugin / ".mcp.json").write_text(json.dumps(
        {"mcpServers": {"x": {"url": "${DEMO_MCP_URL}",
                              "headers": {"Authorization": "Bearer ${DEMO_TOKEN}"}}}}))
    (root / "CLAUDE.md").write_text("Forge rules.\n")
    (root / "outside.txt").write_text("not part of any package\n")
    return root


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    forge_root = make_forge(tmp_path / "forge")
    return Settings(data_dir=tmp_path / "data", forge_local=str(forge_root),
                    signing_key="k" * 40, google_client_id="cid.apps.googleusercontent.com",
                    google_client_secret="not-a-real-value", dev_user=USER)


@pytest.fixture
def store(settings: Settings) -> Store:
    return Store(settings.db_path)


@pytest.fixture
def forge(settings: Settings) -> Forge:
    return Forge(settings)


@pytest.fixture
def call(settings: Settings, store: Store, forge: Forge):
    """call(tool, as_user=..., **args) -> structured result. Raises ToolError on refusal."""
    import anyio

    def _call(tool: str, as_user: str = USER, **args):
        settings.dev_user = as_user
        server = build_server(settings, store, forge)
        result = anyio.run(server.call_tool, tool, args)
        return result.structured_content
    return _call
