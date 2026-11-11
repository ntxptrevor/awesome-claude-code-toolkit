# ntxp-forge-connect

One install that makes a Claude environment start every session from live NTXP Forge.

| Part | What it does |
|---|---|
| `.mcp.json` | Adds the `ntxp-forge` MCP server at `NTXP_FORGE_MCP_URL`. |
| `hooks/hooks.json` | On session start, adds the instruction to call `forge_bootstrap` first. Fails open. |
| `skills/ntxp-forge` | An always-on skill that routes any NTXP task to `skill_load`. |

The plugin holds no NTXP skill content. Every Forge package stays on the server.

## Install

1. Set `NTXP_FORGE_MCP_URL` to `<PUBLIC_URL>/mcp` in the environment or in managed settings.
2. Install this plugin once per account, or list it in managed settings so every account gets it.
3. On first use, sign in with an ntxpllc.com Google Workspace account.

On claude.ai, where hooks do not run, add the connector and paste this line into the organization instructions:

> Before your first reply in every session, call the `forge_bootstrap` tool of the NTXP Forge connector and follow what it returns.
