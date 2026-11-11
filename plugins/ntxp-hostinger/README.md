# ntxp-hostinger

One plugin for Hostinger. It replaces two plugins: `hostinger` (7 deploy skills) and `hostinger-connector-v3` (REST script, local stdio lane, vault token).

| Part | Path | Purpose |
|---|---|---|
| Skill | `skills/hostinger/SKILL.md` | Core tool list, gate rules, failure table |
| Playbooks | `skills/hostinger/references/playbooks.md` | DNS safe-write, domain search, subdomains, 7 deploy types, VPS |
| Catalog | `skills/hostinger/references/catalog/` | 436 operations in 11 area files, read on demand |
| MCP config | `.mcp.json` | Remote HTTP server, OAuth sign-in |
| Server source | `../../mcp-servers/hostinger/` | Stateless, zero dependencies, generated from the Hostinger OpenAPI spec |

## Setup

1. Deploy the server. See `mcp-servers/hostinger/README.md`.
2. Set `HOSTINGER_MCP_URL` to the deployed URL, for example `https://hostinger-mcp.<account>.workers.dev/mcp`.
3. Install the plugin and authorize the `hostinger` server once in the browser.
4. Remove the `hostinger` and `hostinger-connector-v3` plugins.

Without `HOSTINGER_MCP_URL` the plugin connects to Hostinger's hosted server at `https://mcp.hostinger.com`, which exposes `search` and `execute` in place of the tools in the skill.

## What was removed

| Removed | Replacement |
|---|---|
| Local stdio server `npx @hostinger/mcp` (Node 24 on the operator's machine) | Cloud server |
| `scripts/hapi.py` and the `HOSTINGER_API_TOKEN` vault entry | OAuth token from the client |
| `curl` TUS upload from a shell | `hostinger_upload_from_url` |
| Self-hosted gateway on the VPS | Not used |
| 7 deploy skills | One table in the playbooks |
