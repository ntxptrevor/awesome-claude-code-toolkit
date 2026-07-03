# /browserbase:setup

Install and configure the Browserbase plugin: browse CLI, API key, and MCP server.

## Process

1. Check if Node.js is installed (required for the browse CLI and MCP server).
2. Check if the `browse` CLI is installed. If not, install it with `npm install -g browse@latest`.
3. Remove any deprecated CLIs (`@browserbasehq/cli`, `@browserbasehq/browse-cli`) that shadow `browse`.
4. Check for `BROWSERBASE_API_KEY` in the environment or `.env` file.
5. If missing, tell the user to get their key at https://browserbase.com/settings and set it.
6. Write the key to `.env` if not already present.
7. Verify API access by running `browse cloud projects list`.
8. Run the automated setup script:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/setup/install.sh"
   ```
9. Confirm success and list available commands.

## Rules

- Never ask for or set `BROWSERBASE_PROJECT_ID` — it is not needed.
- Leave `MODEL_API_KEY` and other LLM provider keys blank on free-tier accounts.
- The `.mcp.json` in this plugin auto-registers the Browserbase MCP server — no manual Claude settings edits needed.
- If the API key is already set and working, skip straight to the success confirmation.
