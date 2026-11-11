---
name: ntxp-forge
description: "ALWAYS-ON entry point for NTXP work. Use at the start of every session and before any NTXP task (estimating, bids, billing, project documents, dashboards, contracts, credentials, any NTXP skill or plugin by name). Calls the NTXP Forge MCP `forge_bootstrap` tool, then loads the matching skill live with `skill_load`. Holds no skill content of its own."
when-to-use: "NTXP, Forge, any NTXP skill or plugin name, start of session, which skills do we have, load a skill, set up my environment"
user-invocable: true
version: '0.1.0'
owner: NTXP
requires:
  connectors:
  - ntxp-forge
provides:
- forge-bootstrap
- live-skill-loading
---

# NTXP Forge

Every NTXP skill, plugin and instruction is served live by the `ntxp-forge`
MCP server. This skill holds none of them. It tells you how to get them.

1. Call `forge_bootstrap`. Do this once per session, before your first reply.
2. Follow the `instructions` and each `autoloaded` entry it returns.
3. For a task, find the matching package in `catalog`. Call `skill_load` with its name. Follow the entry document it returns.
4. Before a skill's first use, call `env_init` with its name. Run the returned `shell` and `workflows`. File each `ntxp_id_requests` block through the NTXP ID VAULT process.
5. Read a supporting file with `package_file` only when the task needs that file.
6. After the work, call `entry_append` with kind `activity` and the skill name as scope.

## Rules

- Do not save a skill or plugin file into a skills folder, a repo, Drive or memory.
- The server never returns a credential value. Do not ask for one in chat.
- If the tools return a sign-in error, the user must sign in to the connector with an ntxpllc.com Google Workspace account.
