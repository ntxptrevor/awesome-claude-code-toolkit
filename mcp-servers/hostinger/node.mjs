#!/usr/bin/env node
// Node 18+ adapter for hosts without a fetch-handler runtime. Zero dependencies.
import { createServer } from 'node:http';
import { handle } from './src/server.mjs';
import { pinnedFetch } from './src/pinned-fetch.mjs';

const env = { ...process.env, pinnedFetch };

const port = Number(process.env.PORT || 8787);
createServer(async (req, res) => {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const request = new Request(`http://${req.headers.host}${req.url}`, {
    method: req.method,
    headers: req.headers,
    body: chunks.length ? Buffer.concat(chunks) : undefined,
  });
  try {
    const response = await handle(request, env);
    res.writeHead(response.status, Object.fromEntries(response.headers));
    res.end(Buffer.from(await response.arrayBuffer()));
  } catch {
    res.writeHead(500, { 'content-type': 'application/json' });
    res.end('{"error":"internal_error"}');
  }
}).listen(port, () => console.log(`hostinger-mcp on :${port}`));
