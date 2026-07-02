#!/usr/bin/env node
/**
 * First-run bootstrap for the Browserbase connector.
 *
 * The plugin's .mcp.json points here instead of directly at the upstream
 * @browserbasehq/mcp server, so the very first launch configures itself:
 *
 *   1. Loads ~/.config/browserbase-mcp/config.json — written by
 *      /browserbase:setup — and maps it onto the environment (real env vars
 *      always win).
 *   2. No BROWSERBASE_API_KEY / BROWSERBASE_PROJECT_ID? Prints setup
 *      instructions on stderr but still starts the server, so `/mcp` shows a
 *      connection and the first tool call surfaces Browserbase's own error.
 *   3. Prefers a vendored copy of @browserbasehq/mcp bundled at
 *      ${CLAUDE_PLUGIN_ROOT}/vendor/node_modules (present in the
 *      self-contained plugin zip built by scripts/export.sh); falls back to
 *      `npx -y @browserbasehq/mcp` when running from the repo/marketplace
 *      install, which fetches the package on demand.
 *
 * All diagnostics go to stderr — stdout belongs to the MCP protocol.
 */

import { existsSync, readFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const log = (msg) => console.error(`[browserbase-bootstrap] ${msg}`);
const PLUGIN_ROOT = dirname(fileURLToPath(import.meta.url));

export const CONFIG_DIR =
  process.env.BROWSERBASE_CONFIG_DIR || join(homedir(), ".config", "browserbase-mcp");
export const CONFIG_PATH =
  process.env.BROWSERBASE_CONFIG_PATH || join(CONFIG_DIR, "config.json");

const PASSTHROUGH_KEYS = [
  "BROWSERBASE_API_KEY",
  "BROWSERBASE_PROJECT_ID",
  "GEMINI_API_KEY",
  "MODEL_API_KEY",
];

function readConfig() {
  try {
    return JSON.parse(readFileSync(CONFIG_PATH, "utf8"));
  } catch {
    return {};
  }
}

const config = readConfig();

// Config file -> environment; real env vars always win.
for (const key of PASSTHROUGH_KEYS) {
  if (process.env[key] === undefined && config[key] != null && config[key] !== "") {
    process.env[key] = String(config[key]);
  }
}

const hasAuth = process.env.BROWSERBASE_API_KEY && process.env.BROWSERBASE_PROJECT_ID;
if (!hasAuth) {
  log("no Browserbase credentials found (BROWSERBASE_API_KEY / BROWSERBASE_PROJECT_ID).");
  log("get a free API key + project ID at https://www.browserbase.com/settings");
  log(`then run /browserbase:setup to link them (writes ${CONFIG_PATH}, chmod 600).`);
  log("starting anyway — tool calls will fail with Browserbase's own auth error until linked.");
}

// CLI flags, mapped from the same config file (all optional).
const args = [];
if (config.MODEL_NAME) args.push("--modelName", String(config.MODEL_NAME));
if (process.env.MODEL_API_KEY) args.push("--modelApiKey", process.env.MODEL_API_KEY);
if (config.PROXIES) args.push("--proxies");
if (config.VERIFIED) args.push("--verified");
if (config.KEEP_ALIVE) args.push("--keepAlive");
if (config.CONTEXT_ID) args.push("--contextId", String(config.CONTEXT_ID));
if (config.BROWSER_WIDTH) args.push("--browserWidth", String(config.BROWSER_WIDTH));
if (config.BROWSER_HEIGHT) args.push("--browserHeight", String(config.BROWSER_HEIGHT));

const vendoredEntry = join(PLUGIN_ROOT, "vendor", "node_modules", "@browserbasehq", "mcp", "cli.js");
const useVendored = existsSync(vendoredEntry);

const command = useVendored ? "node" : "npx";
const spawnArgs = useVendored ? [vendoredEntry, ...args] : ["-y", "@browserbasehq/mcp", ...args];

if (useVendored) log("using vendored @browserbasehq/mcp (self-contained plugin install).");

const child = spawn(command, spawnArgs, {
  stdio: "inherit",
  env: process.env,
  shell: process.platform === "win32",
});
child.on("exit", (code, signal) => process.exit(code ?? (signal ? 1 : 0)));
child.on("error", (err) => {
  log(`failed to start Browserbase MCP server: ${err.message}`);
  process.exit(1);
});
