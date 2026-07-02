#!/usr/bin/env node
/**
 * SessionStart hook: one quiet line of context when the Browserbase connector
 * is not yet linked to an account, so Claude knows to offer
 * /browserbase:setup. Prints nothing once configured. Never blocks (always
 * exits 0).
 */

try {
  const { readFileSync } = await import("node:fs");
  const { homedir } = await import("node:os");
  const { join } = await import("node:path");

  const configPath =
    process.env.BROWSERBASE_CONFIG_PATH || join(homedir(), ".config", "browserbase-mcp", "config.json");

  let config = {};
  try {
    config = JSON.parse(readFileSync(configPath, "utf8"));
  } catch {}

  const linked =
    process.env.BROWSERBASE_API_KEY ||
    process.env.BROWSERBASE_PROJECT_ID ||
    (config.BROWSERBASE_API_KEY && config.BROWSERBASE_PROJECT_ID);

  if (!linked) {
    console.log(
      "Browserbase connector: not linked to an account yet — tool calls will fail until " +
        "credentials are set. Offer /browserbase:setup when the user wants to browse the web."
    );
  }
} catch {
  // Never block session start.
}
process.exit(0);
