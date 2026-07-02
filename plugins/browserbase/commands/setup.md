# /browserbase:setup

Link the user's Browserbase account to the connector. This is a config-file
edit, not a build step — the MCP server itself is the published
`@browserbasehq/mcp` package, fetched on demand by `bootstrap.mjs`.

Config lives at `~/.config/browserbase-mcp/config.json` (chmod 600).

## Steps

1. **Check for existing config.** If `~/.config/browserbase-mcp/config.json`
   already has `BROWSERBASE_API_KEY`, confirm with the user before replacing
   it — they may just want to change a secondary setting (step 3).

2. **Get credentials.** Ask the user for:
   - Their **Browserbase API key** and **project ID**, from
     https://www.browserbase.com/settings (free tier available, no credit
     card required for the starter plan).
   - Treat both as secrets: write them to the config file, don't echo them
     back in full (mask all but the last 4 characters when confirming).

   Write (creating the directory with `mkdir -p ~/.config/browserbase-mcp`
   first, and `chmod 600` the file after writing):

   ```json
   {
     "BROWSERBASE_API_KEY": "<key>",
     "BROWSERBASE_PROJECT_ID": "<project id>"
   }
   ```

3. **Optional model provider.** The default model
   (`google/gemini-2.5-flash-lite`) needs a `GEMINI_API_KEY` in the same
   config file. If the user would rather use a different provider (e.g.
   Claude itself, or OpenAI), ask which, then add:

   ```json
   {
     "MODEL_NAME": "anthropic/claude-haiku-4-5",
     "MODEL_API_KEY": "<provider api key>"
   }
   ```

   If they skip this entirely, `act`/`observe`/`extract` calls will fail
   until either `GEMINI_API_KEY` or `MODEL_NAME`+`MODEL_API_KEY` is set —
   tell them this plainly rather than leaving it silent.

4. **Optional session settings.** Only ask if the user brings it up:
   `PROXIES` (route through Browserbase proxies), `KEEP_ALIVE` (keep sessions
   alive across calls), `CONTEXT_ID` (reuse cookies/storage across runs),
   `BROWSER_WIDTH`/`BROWSER_HEIGHT` (viewport size).

5. **Verify.** The MCP server may have started before credentials existed —
   tell the user to run `/mcp` and reconnect `browserbase` (or restart the
   session). Then call the `start` tool followed by `navigate` to
   `https://example.com`: a successful navigate confirms the link. If it
   errors, re-check the API key and project ID for typos.

6. **Offer next steps.** Point at `/browserbase:scrape-page`,
   `/browserbase:fill-form`, and `/browserbase:browse-agent`.

## Safety

- API keys are secrets: only ever store them in
  `~/.config/browserbase-mcp/config.json` (mode 600) or the environment —
  never in this repo, never in chat output, never in logs.
- If a key was ever pasted into a chat message, tell the user to rotate it at
  browserbase.com/settings before relying on it — chat history is not a safe
  place for live credentials.
