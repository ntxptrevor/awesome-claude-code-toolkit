#!/usr/bin/env node
/**
 * Tesla connector MCP server (stdio).
 *
 * Exposes the entire tool registry — every Fleet/Owner API data endpoint and
 * remote command, plus the convenience tools (find my Tesla, drop a pin,
 * navigate-to-car, lock/unlock) — to any MCP client: Claude Code, Claude
 * Desktop, ChatGPT (via MCP connectors), or anything else that speaks MCP.
 *
 * Credentials come from the environment (see README):
 *   TESLA_REFRESH_TOKEN  — app-style refresh token (owner mode), or
 *   TESLA_CLIENT_ID/SECRET + TESLA_REFRESH_TOKEN — Fleet API mode
 *   TESLA_MOCK=1         — demo mode, no credentials needed
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadConfig } from "./config.js";
import { TeslaClient } from "./client.js";
import { TOOLS } from "./tools.js";

function ok(data: unknown) {
  return {
    content: [{ type: "text" as const, text: typeof data === "string" ? data : JSON.stringify(data, null, 2) }],
  };
}

function fail(err: unknown) {
  const message = err instanceof Error ? err.message : String(err);
  return { isError: true, content: [{ type: "text" as const, text: `Error: ${message}` }] };
}

const config = loadConfig();
const client = new TeslaClient(config);
const server = new McpServer({ name: "tesla", version: "0.1.0" });

for (const tool of TOOLS) {
  server.tool(tool.name, tool.description, tool.schema, async (args: Record<string, unknown>) => {
    try {
      return ok(await tool.handler(client, args ?? {}));
    } catch (err) {
      return fail(err);
    }
  });
}

const transport = new StdioServerTransport();
await server.connect(transport);
console.error(
  `[tesla-mcp] ready — ${TOOLS.length} tools, mode=${config.mock ? "MOCK" : config.mode}, base=${config.apiBase}`
);
