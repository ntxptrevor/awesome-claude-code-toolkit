import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { handle, buildRequest, CORE } from '../src/server.mjs';
import { OPS } from '../src/catalog.mjs';

const BASE = 'https://mcp.example.com';
let calls;
let responder;
let dns;
beforeEach(() => {
  calls = [];
  responder = () => new Response('{"ok":true}', { status: 200 });
  dns = { A: ['93.184.216.34'], AAAA: [] };
  globalThis.fetch = async (url, init = {}) => {
    if (String(url).startsWith('https://cloudflare-dns.com/')) {
      if (!dns) return new Response('', { status: 500 });
      const type = new URL(url).searchParams.get('type');
      return Response.json({ Answer: dns[type].map((data) => ({ type: type === 'A' ? 1 : 28, data })) });
    }
    calls.push({ url: String(url), ...init });
    return responder(String(url), init);
  };
});

const post = (body, headers = { authorization: 'Bearer tok' }, path = '/mcp') =>
  handle(new Request(BASE + path, { method: 'POST', headers: { 'content-type': 'application/json', ...headers }, body: JSON.stringify(body) }));
const rpc = async (method, params, headers) => (await post({ jsonrpc: '2.0', id: 1, method, params }, headers)).json();
const tool = (name, args) => rpc('tools/call', { name, arguments: args });

test('no bearer gives 401 with resource metadata pointer', async () => {
  const res = await post({ jsonrpc: '2.0', id: 1, method: 'tools/list' }, {});
  assert.equal(res.status, 401);
  assert.match(res.headers.get('www-authenticate'), /resource_metadata="https:\/\/mcp\.example\.com\/\.well-known\/oauth-protected-resource"/);
});

test('protected resource metadata names Hostinger as the authorization server', async () => {
  const res = await handle(new Request(BASE + '/.well-known/oauth-protected-resource/mcp'));
  const meta = await res.json();
  assert.equal(meta.resource, BASE + '/mcp');
  assert.deepEqual(meta.authorization_servers, ['https://auth.hostinger.com']);
});

test('initialize negotiates the protocol version and keeps no session', async () => {
  const res = await post({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2025-06-18' } });
  assert.equal(res.headers.get('mcp-session-id'), null);
  assert.equal((await res.json()).result.protocolVersion, '2025-06-18');
});

test('notification returns 202', async () => {
  const res = await post({ jsonrpc: '2.0', method: 'notifications/initialized' });
  assert.equal(res.status, 202);
});

test('tools/list exposes only the core set plus four gate tools', async () => {
  const { result } = await rpc('tools/list');
  const names = result.tools.map((t) => t.name);
  assert.equal(names.length, CORE.length + 4);
  for (const n of ['DNS_getDNSRecordsV1', 'dns_set_cname', 'hosting_createWebsiteSubdomainV1', 'hostinger_call', 'hostinger_describe']) {
    assert.ok(names.includes(n), n);
  }
  assert.ok(!names.includes('VPS_getVirtualMachinesV1'));
  assert.ok(JSON.stringify(result).length < 40000, 'tool list stays small');
  for (const t of result.tools) assert.match(t.name, /^[A-Za-z0-9_-]{1,64}$/);
});

test('every core operation exists in the catalog', () => {
  for (const id of CORE) assert.ok(OPS[id], id);
});

test('core tool forwards the bearer and splits path, query and body', async () => {
  await tool('hosting_createWebsiteSubdomainV1', { username: 'u1', domain: 'example.com', subdomain: 'app' });
  assert.equal(calls[0].method, 'POST');
  assert.equal(calls[0].url, 'https://developers.hostinger.com/api/hosting/v1/accounts/u1/websites/example.com/subdomains');
  assert.equal(calls[0].headers.authorization, 'Bearer tok');
  assert.deepEqual(JSON.parse(calls[0].body), { subdomain: 'app' });
});

test('query arguments go to the query string', () => {
  const r = buildRequest('hosting_listWebsitesV1', { domain: 'example.com' });
  assert.equal(r.method, 'GET');
  assert.match(r.url, /\/api\/hosting\/v1\/websites\?domain=example\.com$/);
  assert.equal(r.body, undefined);
});

test('missing and unknown arguments are rejected before any network call', async () => {
  const a = await tool('DNS_getDNSRecordsV1', {});
  assert.ok(a.result.isError);
  const b = await tool('DNS_getDNSRecordsV1', { domain: 'example.com', nope: 1 });
  assert.ok(b.result.isError);
  assert.equal(calls.length, 0);
});

test('hostinger_call runs a read without confirm', async () => {
  const out = await tool('hostinger_call', { operation: 'VPS_getVirtualMachinesV1' });
  assert.ok(!out.result.isError);
  assert.equal(calls[0].url, 'https://developers.hostinger.com/api/vps/v1/virtual-machines');
});

test('hostinger_call blocks a write, a delete and a purchase without confirm', async () => {
  for (const operation of ['VPS_restartVirtualMachineV1', 'hosting_deleteWebsiteV1', 'domains_purchaseNewDomainV1']) {
    const out = await tool('hostinger_call', { operation, params: {} });
    assert.ok(out.result.isError, operation);
    assert.match(out.result.content[0].text, /did not run/);
  }
  assert.equal(calls.length, 0);
});

test('hostinger_call runs a write with confirm and accepts the dotted operationId', async () => {
  await tool('hostinger_call', { operation: 'hosting_restartNode.jsApplicationV1', params: { username: 'u', domain: 'd.com' }, confirm: true });
  assert.equal(calls[0].method, 'POST');
  assert.match(calls[0].url, /\/nodejs\/server\/restart$/);
});

test('hostinger_describe returns the schema and suggests on a miss', async () => {
  const hit = await tool('hostinger_describe', { operation: 'DNS_updateDNSRecordsV1' });
  const d = JSON.parse(hit.result.content[0].text);
  assert.equal(d.method, 'PUT');
  assert.ok(d.inputSchema.properties.zone);
  const miss = await tool('hostinger_describe', { operation: 'firewall list' });
  assert.match(miss.result.content[0].text, /VPS_getFirewallListV1/);
});

test('dns_set_cname validates first and stops on a validation error', async () => {
  responder = (url) => (url.endsWith('/validate') ? new Response('{"message":"bad"}', { status: 422 }) : new Response('{}'));
  const out = await tool('dns_set_cname', { domain: 'example.com', name: 'www', target: 'x.pages.dev' });
  assert.ok(out.result.isError);
  assert.equal(calls.length, 1);
});

test('dns_set_cname writes one CNAME record after validation passes', async () => {
  await tool('dns_set_cname', { domain: 'example.com', name: 'www', target: 'x.pages.dev' });
  assert.equal(calls.length, 2);
  assert.equal(calls[1].method, 'PUT');
  assert.deepEqual(JSON.parse(calls[1].body), {
    overwrite: true,
    zone: [{ name: 'www', type: 'CNAME', ttl: 14400, records: [{ content: 'x.pages.dev' }] }],
  });
});

test('upstream 401 becomes an HTTP 401 so the client refreshes its token', async () => {
  responder = () => new Response('{"message":"Unauthenticated."}', { status: 401 });
  const res = await post({ jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name: 'domains_getDomainListV1', arguments: {} } });
  assert.equal(res.status, 401);
  assert.ok(res.headers.get('www-authenticate'));
});

test('upstream error is a tool error with the status', async () => {
  responder = () => new Response('{"message":"Too many"}', { status: 429, headers: { 'retry-after': '30' } });
  const out = await tool('domains_getDomainListV1', {});
  assert.ok(out.result.isError);
  assert.match(out.result.content[0].text, /429.*retry after 30s/);
});

test('upload tool rejects private and non-https URLs', async () => {
  const args = { upload_url: 'https://files.hostingerfiles.net/u', auth_key: 'a', rest_auth_key: 'b', path: 'site.zip' };
  for (const source_url of ['http://cdn.example.org/a.zip', 'https://127.0.0.1/a.zip', 'https://localhost/a.zip', 'https://2130706433/a.zip', 'https://0x7f.1/a.zip', 'https://017700000001/a.zip', 'https://[::1]/a.zip', 'https://user@cdn.example.org/a.zip', 'https://cdn.example.org:8443/a.zip']) {
    const out = await tool('hostinger_upload_from_url', { ...args, source_url });
    assert.ok(out.result.isError, source_url);
  }
  assert.equal(calls.length, 0);
});

test('upload tool runs TUS create then patch and never sends the bearer', async () => {
  responder = (url, init) => {
    if (url.startsWith('https://cdn.acme.org')) return new Response(new Uint8Array(5));
    if (init.method === 'POST') return new Response(null, { status: 201 });
    return new Response(null, { status: 204, headers: { 'upload-offset': '5' } });
  };
  const out = await tool('hostinger_upload_from_url', {
    upload_url: 'https://files.hostingerfiles.net/u', auth_key: 'a', rest_auth_key: 'b', source_url: 'https://cdn.acme.org/site.zip', path: 'site.zip',
  });
  assert.deepEqual(JSON.parse(out.result.content[0].text), { uploaded: 'site.zip', bytes: 5 });
  assert.equal(calls[1].url, 'https://files.hostingerfiles.net/u/site.zip?override=true');
  assert.equal(calls[1].headers['upload-length'], '5');
  for (const c of calls) assert.equal(c.headers?.authorization, undefined);
});

test('GET on the MCP endpoint is 405 and unknown paths are 404', async () => {
  assert.equal((await handle(new Request(BASE + '/mcp'))).status, 405);
  assert.equal((await handle(new Request(BASE + '/nope'))).status, 404);
});

test('every operation named in the skill exists in the spec', async () => {
  const { readFile } = await import('node:fs/promises');
  const dir = new URL('../../../plugins/ntxp-hostinger/skills/hostinger/', import.meta.url);
  const extra = new Set(['dns_set_cname', 'hostinger_describe', 'hostinger_call', 'hostinger_upload_from_url']);
  for (const file of ['SKILL.md', 'references/playbooks.md']) {
    const md = await readFile(new URL(file, dir), 'utf8');
    const names = [...md.matchAll(/`([A-Za-z-]+_[A-Za-z.]+V1|[a-z]+_[a-z_]+)`/g)].map((m) => m[1]);
    assert.ok(names.length > 10, file);
    for (const n of names) {
      if (/^[a-z_]+$/.test(n) && !extra.has(n)) continue; // field names such as archive_path
      assert.ok(OPS[n] || extra.has(n), `${file}: ${n}`);
    }
  }
});

test('authorization server metadata returns 502 when the issuer is unreachable', async () => {
  responder = () => { throw new Error('network down'); };
  const res = await handle(new Request(BASE + '/.well-known/oauth-authorization-server'));
  assert.equal(res.status, 502);
});

test('upload tool refuses a redirect to a private host', async () => {
  responder = (url) =>
    url.startsWith('https://cdn.acme.org')
      ? new Response(null, { status: 302, headers: { location: 'https://169.254.169.254/latest/meta-data' } })
      : new Response('private data');
  const out = await tool('hostinger_upload_from_url', {
    upload_url: 'https://files.hostingerfiles.net/u', auth_key: 'a', rest_auth_key: 'b', source_url: 'https://cdn.acme.org/site.zip', path: 'site.zip',
  });
  assert.ok(out.result.isError);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].redirect, 'manual');
});

test('a network failure on a tool call is a tool error', async () => {
  responder = () => { throw new Error('network down'); };
  const out = await tool('domains_getDomainListV1', {});
  assert.ok(out.result.isError);
});

test('upload tool refuses a public name that resolves to a private address', async () => {
  const args = { upload_url: 'https://files.hostingerfiles.net/u', auth_key: 'a', rest_auth_key: 'b', source_url: 'https://rebind.acme.org/a.zip', path: 'site.zip' };
  for (const records of [{ A: ['10.0.0.5'], AAAA: [] }, { A: ['93.184.216.34'], AAAA: ['fd00::1'] }, { A: ['169.254.169.254'], AAAA: [] }, { A: [], AAAA: ['::ffff:127.0.0.1'] }, { A: [], AAAA: [] }]) {
    dns = records;
    const out = await tool('hostinger_upload_from_url', args);
    assert.ok(out.result.isError, JSON.stringify(records));
  }
  assert.equal(calls.length, 0);
});

test('upload tool fails closed when the name cannot be resolved', async () => {
  dns = null;
  const out = await tool('hostinger_upload_from_url', {
    upload_url: 'https://files.hostingerfiles.net/u', auth_key: 'a', rest_auth_key: 'b', source_url: 'https://cdn.acme.org/a.zip', path: 'site.zip',
  });
  assert.ok(out.result.isError);
  assert.equal(calls.length, 0);
});
