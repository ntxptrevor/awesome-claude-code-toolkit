# Browserbase Connector

Cloud browser automation from Claude Code and Claude chat, via
[Browserbase](https://www.browserbase.com/) + [Stagehand](https://stagehand.dev/).
Gives Claude real, headless cloud Chrome sessions it can navigate, click
through, fill forms in, and extract structured data from — no local browser
install, no CAPTCHIA-prone headless-Chrome-on-your-laptop setup.

## What you get

- **6 MCP tools**: `start`, `end`, `navigate`, `act`, `observe`, `extract`
- **Zero-touch first run**: the plugin starts in an unlinked state and tells
  Claude to offer `/browserbase:setup` the first time browsing comes up —
  nothing to configure by hand before that
- **3 task-shaped slash commands**: `/browserbase:scrape-page`,
  `/browserbase:fill-form`, `/browserbase:browse-agent`
- Backed by the official [`@browserbasehq/mcp`](https://github.com/browserbase/mcp-server-browserbase)
  server; this plugin only adds the setup/config layer on top

## Install

**Plugin marketplace:**

```
/plugin marketplace add rohitg00/awesome-claude-code-toolkit
/plugin install browserbase
```

**Manual (clone + point Claude Code at the plugin dir):** see the repo root
README's Quick Install section.

## First run

1. Start a session. If you're not linked yet, Claude will mention
   `/browserbase:setup` when you ask it to browse or scrape something.
2. Run `/browserbase:setup`. It asks for your Browserbase API key and project
   ID (free tier available at [browserbase.com](https://www.browserbase.com/settings))
   and writes them to `~/.config/browserbase-mcp/config.json` (chmod 600) —
   **never** into this repo or plugin directory.
3. Reconnect the MCP server (`/mcp` → reconnect `browserbase`, or restart the
   session) and try `/browserbase:scrape-page` on any URL.

## Configuration reference

All keys live in `~/.config/browserbase-mcp/config.json`:

| Key | Required | Purpose |
|-----|----------|---------|
| `BROWSERBASE_API_KEY` | yes | Auth for all Browserbase API calls |
| `BROWSERBASE_PROJECT_ID` | yes | Which Browserbase project sessions bill to |
| `GEMINI_API_KEY` | no | Powers the default model (`google/gemini-2.5-flash-lite`) for `act`/`observe`/`extract` |
| `MODEL_NAME` | no | Use a different model, e.g. `anthropic/claude-haiku-4-5` |
| `MODEL_API_KEY` | no | API key for `MODEL_NAME`'s provider (required if `MODEL_NAME` is set to a non-Gemini model) |
| `PROXIES` | no | `true` to route sessions through Browserbase proxies |
| `VERIFIED` | no | `true` to enable Verified Identity (Scale plan only) |
| `KEEP_ALIVE` | no | `true` to keep sessions alive between tool calls |
| `CONTEXT_ID` | no | Reuse a persistent Browserbase context (cookies/storage) |
| `BROWSER_WIDTH` / `BROWSER_HEIGHT` | no | Viewport size (defaults 1024×768) |

Environment variables of the same name always override the config file, so
CI/headless setups can skip the file entirely and export vars directly.

## Skill and agent

- `skills/browserbase-automation/` — reference for the Stagehand tool
  contract, prompt patterns for `act`/`extract`/`observe`, and speed/cost
  tips. Load this any time to write good automation without the plugin.
- `agents/specialized-domains/browser-automation-engineer.md` — a specialist
  persona for designing multi-step scraping/automation flows.

## Packaging

`scripts/export.sh` builds two self-contained artifacts under `build/`:

- `browserbase.mcpb` — one-click install in Claude Desktop
  (`npx @anthropic-ai/mcpb install build/browserbase.mcpb`)
- `browserbase-plugin.zip` — this plugin with `@browserbasehq/mcp` vendored
  into `vendor/node_modules`, so `bootstrap.mjs` runs with no network fetch
  and no repo clone required on the target machine

## Security

- Credentials are only ever written to `~/.config/browserbase-mcp/config.json`
  (mode 600) or the environment — never to this repo, never echoed in chat,
  never logged.
- If you shared a live API key in chat by mistake, rotate it immediately at
  [browserbase.com/settings](https://www.browserbase.com/settings) — anything
  pasted into a conversation should be treated as compromised.
