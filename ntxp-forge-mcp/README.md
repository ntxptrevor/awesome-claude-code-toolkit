# NTXP Forge MCP

One MCP endpoint for every NTXP skill and plugin. A user adds one connector,
signs in with Google, and loads skills live from the private NTXP Forge repo.
No skill is installed or copied into the user's environment.

## What it does

| Need | How the server meets it |
|---|---|
| Stateless MCP | Streamable HTTP in stateless mode (`mcp` 2.x, protocol `2026-07-28`). Each POST is complete. No session id. |
| Google sign-in | The server is the OAuth server Claude sees and sends the person to Google. A verified Workspace account with hosted domain `ntxpllc.com` is approved. All others are refused and logged. |
| Roles | `trevor@ntxpllc.com` is `admin`: read, write, delete. Every other domain account is `user`: read only, plus append to change logs, activity lists and usage notes. Both values are constants in `config.py`. |
| Access log | SQLite table `access_log`: user, timestamp, date stamp, time stamp, action (read, write, delete, copy, auth, sync), tool, target, outcome, flag, reason. Triggers block update and delete. |
| Forge back end | One shallow checkout of `NTXP-TX/ntxp-forge`, refreshed when older than 300 seconds. A failed fetch keeps the last good copy and reports `stale`. |
| NTXP ID | The server will not start until its 4 credentials are set. It prints one `NTXP ID VAULT REQUEST` block per missing credential. It never returns a credential value. |
| No duplicate skills | `skill_load` returns the entry document on demand. `package_file` returns one file per call. Per-user settings are `.md` files under `user-config/` in the server data folder. |
| No wholesale copy | `package_export` is admin only. A non-admin who reads more than 12 files of one package, or 40 files in total, in 15 minutes is refused. Both are logged with action `copy`. |
| Other users' records | A user is refused and logged (`cross_user`). The admin must give a reason of 10 or more characters, which is logged. |

## Tools

| Tool | Action | User | Admin |
|---|---|---|---|
| `forge_bootstrap`, `whoami`, `ntxp_id_status`, `catalog_list` | read | yes | yes |
| `skill_load`, `package_file`, `env_init` | read | yes (file limit) | yes |
| `entry_append`, `entry_list` | write, read | yes | yes |
| `entry_delete` | delete | no | yes |
| `config_list`, `config_read` | read | own files | any, with reason |
| `config_write`, `config_delete` | write, delete | no | yes |
| `package_export` | copy | no (logged) | yes, with reason |
| `forge_sync` | read; `force` is sync | status only | yes |
| `access_log` | read | own rows | any, with reason |

## Auto deploy

Four parts make a connected environment start from live Forge with no per-skill install.

| Part | Where it runs | Effect |
|---|---|---|
| Server instructions | Every MCP client | Tell the model to call `forge_bootstrap` before its first reply. They also list every Forge package by name, rebuilt after each sync. |
| Prompts | Every MCP client | One prompt per skill and plugin, shown in the client's prompt menu. A merge to Forge adds or removes prompts with no reinstall. |
| `autoload` | `forge_bootstrap` | A package whose `mcp-init.json` sets `"autoload": true` sends its entry document with the bootstrap. Limit: 8 packages. |
| `plugin/ntxp-forge-connect` | Claude Code, Cowork, desktop | One plugin: the connector, a session-start hook that orders the bootstrap call, and one router skill. It holds no Forge content. |

On claude.ai, hooks do not run. Add the connector and put this line in the organization instructions:

> Before your first reply in every session, call the `forge_bootstrap` tool of the NTXP Forge connector and follow what it returns.

Hooks, slash commands and bundled MCP servers inside a Forge plugin still need a native install. The connector serves their files; it cannot run them.

## Deploy a skill to users in one task

1. Merge the skill or plugin to NTXP Forge `main`. The server serves it within 300 seconds.
2. Optional: add `mcp-init.json` to the package.

```json
{
  "env": {
    "DEMO_REGION": {"value": "us-central"},
    "DEMO_API_KEY": {"vault_title": "Demo service"}
  },
  "workflows": [{"name": "install", "run": "pip install -r requirements.txt"}]
}
```

3. The user's agent calls `forge_bootstrap(skills=["<name>"])`. The result holds the role, the catalog, the Forge instructions, a shell snippet for non-credential values, the workflows, and one NTXP ID request per credential.

## Run

Get each value through the NTXP ID VAULT process, then set it in the server environment.

| Variable | Purpose |
|---|---|
| `NTXP_FORGE_MCP_GOOGLE_CLIENT_ID` | Google OAuth client id |
| `NTXP_FORGE_MCP_GOOGLE_CLIENT_SECRET` | Google OAuth client value |
| `NTXP_FORGE_MCP_SIGNING_KEY` | 32 or more characters; signs the server's tokens |
| `NTXP_FORGE_MCP_GITHUB_TOKEN` | Read-only token for the Forge repo |
| `NTXP_FORGE_MCP_PUBLIC_URL` | Public https URL of the server |
| `NTXP_FORGE_MCP_HOST`, `_PORT` | Bind address (default `127.0.0.1:8765`) |
| `NTXP_FORGE_MCP_DATA_DIR` | Database, checkout and user config (default `~/.ntxp/forge-mcp`) |
| `NTXP_FORGE_MCP_REPO`, `_REF`, `_SYNC_TTL` | Forge source (default `NTXP-TX/ntxp-forge`, `main`, `300`) |

In the Google Cloud console, add `<PUBLIC_URL>/oauth/google/callback` as an authorized redirect URI.

```bash
pip install -e ".[dev]"
```

```bash
ntxp-forge-mcp check
```

```bash
ntxp-forge-mcp serve
```

Add `<PUBLIC_URL>/mcp` as a custom connector in Claude. For one person on one machine, `ntxp-forge-mcp stdio` runs without sign-in as `NTXP_FORGE_MCP_DEV_USER`.

```bash
ntxp-forge-mcp log --flagged
```

## Test

```bash
python3 -m pytest -q
```

## Limits

- Sync is one way: Forge to server. Entries and config files stay in the server data folder.
- A skill that needs more than 12 of its own files to run is blocked for non-admins. Raise `NTXP_FORGE_MCP_COPY_MAX_PER_PACKAGE` for that case.
- Skills arrive as tool results. They do not appear in Claude's native skill list.
