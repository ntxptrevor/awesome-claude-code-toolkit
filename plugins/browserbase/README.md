# Browserbase Plugin

Cloud browser automation for Claude Code — scrape pages, fill forms, extract structured data, and drive browsers with natural language via [Browserbase](https://browserbase.com) and [Stagehand](https://docs.browserbase.com/welcome/quickstarts/stagehand).

## Quick Install

1. Copy or symlink this plugin folder into your project's `plugins/` directory
2. Set your API key:
   ```bash
   export BROWSERBASE_API_KEY=bb_live_...
   # or add to .env
   ```
3. The plugin auto-configures:
   - **MCP server** registers via `.mcp.json` (no manual settings edit)
   - **SessionStart hook** verifies CLI + API key on every session
   - **UserPromptSubmit hook** detects browser/scraping intent and routes to the plugin
   - **Setup command** installs the `browse` CLI and validates everything

## Commands

| Command | What it does |
|---------|-------------|
| `/browserbase:setup` | Install CLI, configure API key, verify access |
| `/browserbase:scrape-page` | Scrape and extract structured data from a web page |
| `/browserbase:fill-form` | Fill out and submit a web form |
| `/browserbase:browse-agent` | Run an open-ended browsing agent |

## What's Inside

```
browserbase/
├── .claude-plugin/plugin.json   # Plugin manifest
├── .mcp.json                    # Auto-registers Browserbase MCP server
├── README.md
├── agents/
│   └── browser-automation-engineer.md
├── agent-skill/
│   └── SKILL.md                 # Stagehand API reference + patterns
├── commands/
│   ├── setup.md
│   ├── scrape-page.md
│   ├── fill-form.md
│   └── browse-agent.md
├── hooks/
│   ├── hooks.json               # SessionStart + UserPromptSubmit hooks
│   └── scripts/
│       ├── detect-browser-intent.js
│       └── verify-setup.sh
└── setup/
    └── install.sh               # Automated setup script
```

## Requirements

- Node.js 18+
- `BROWSERBASE_API_KEY` (get yours at https://browserbase.com/settings)
- No `BROWSERBASE_PROJECT_ID` needed — the API key resolves it automatically

## Free-Tier Notes

- Model Gateway includes $5 of LLM tokens — leave `MODEL_API_KEY` blank to use it
- No Proxies or Verified sessions — bot-protected sites may block
- If LLM calls fail on a working script, the $5 cap is likely the cause
