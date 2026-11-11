// Hostinger MCP server: stateless, zero dependencies, OAuth bearer pass-through.
// One fetch handler. Runs on Cloudflare Workers, Vercel Edge, Deno Deploy and Node 18+.
//
// The server stores nothing. The MCP client signs the user in at auth.hostinger.com
// (OAuth 2.1, PKCE, dynamic client registration) and sends the access token on every
// request. The server forwards that token to the Hostinger REST API.
import { OPS, SPEC_VERSION } from './catalog.mjs';

const NAME = 'hostinger-mcp';
const VERSION = '1.0.0';
const PROTOCOLS = ['2025-11-25', '2025-06-18', '2025-03-26', '2024-11-05'];
const DEFAULTS = {
  HOSTINGER_API_URL: 'https://developers.hostinger.com',
  HOSTINGER_OAUTH_ISSUER: 'https://auth.hostinger.com',
  MAX_RESULT_BYTES: '120000',
  MAX_UPLOAD_BYTES: '52428800',
  DOH_URL: 'https://cloudflare-dns.com/dns-query',
};

// Tools that stay in the client's tool list at all times: domains, DNS and CNAME,
// subdomains, and basic hosting. Every other operation goes through hostinger_call.
export const CORE = [
  'domains_getDomainListV1',
  'domains_getDomainDetailsV1',
  'domains_checkDomainAvailabilityV1',
  'domains_updateDomainNameserversV1',
  'DNS_getDNSRecordsV1',
  'DNS_validateDNSRecordsV1',
  'DNS_updateDNSRecordsV1',
  'DNS_deleteDNSRecordsV1',
  'DNS_getDNSSnapshotListV1',
  'DNS_restoreDNSSnapshotV1',
  'hosting_listWebsitesV1',
  'hosting_listOrdersV1',
  'hosting_startWebsiteSetupV1',
  'hosting_listWebsiteSetupsV1',
  'hosting_listWebsiteSubdomainsV1',
  'hosting_createWebsiteSubdomainV1',
  'hosting_deleteWebsiteSubdomainV1',
];

const CLASS = { r: 'read', w: 'write', d: 'destructive', $: 'spends money' };

const EXTRA_TOOLS = [
  {
    name: 'dns_set_cname',
    description:
      'Point one name at a target host with a CNAME record. Validates the record first, then replaces any existing CNAME for that name. Other record types and other names stay as they are.',
    inputSchema: {
      type: 'object',
      properties: {
        domain: { type: 'string', description: 'Zone, for example example.com' },
        name: { type: 'string', description: 'Record name without the zone, for example www or app' },
        target: { type: 'string', description: 'Host the name points to, for example example.pages.dev' },
        ttl: { type: 'integer', description: 'Seconds. Default 14400.' },
      },
      required: ['domain', 'name', 'target'],
    },
    annotations: { destructiveHint: true, idempotentHint: true },
  },
  {
    name: 'hostinger_describe',
    description:
      'Return the argument schema, HTTP method, path and class of one Hostinger operation. The operation names are listed in the hostinger skill catalog. An unknown name returns the closest matches.',
    inputSchema: {
      type: 'object',
      properties: { operation: { type: 'string', description: 'operationId, for example VPS_getVirtualMachinesV1' } },
      required: ['operation'],
    },
    annotations: { readOnlyHint: true },
  },
  {
    name: 'hostinger_call',
    description:
      'Run any Hostinger API operation by operationId. params is one flat object with the path, query and body fields from hostinger_describe. An operation that writes, deletes or spends money runs only with confirm set to true, after the user approved that exact action.',
    inputSchema: {
      type: 'object',
      properties: {
        operation: { type: 'string' },
        params: { type: 'object', description: 'Flat arguments for the operation' },
        confirm: { type: 'boolean', description: 'true only after the user approved this write' },
      },
      required: ['operation'],
    },
    annotations: { destructiveHint: true, openWorldHint: true },
  },
  {
    name: 'hostinger_upload_from_url',
    description:
      'Copy a file from an HTTPS URL into Hostinger file storage (TUS upload). Use the url, auth_key and rest_auth_key from hosting_generateUploadURLV1 or agency-hosting_generateUploadURLV1. Then call the deploy, build or import operation. No shell or local file is needed.',
    inputSchema: {
      type: 'object',
      properties: {
        upload_url: { type: 'string', description: 'url from the generate-upload-URL operation' },
        auth_key: { type: 'string' },
        rest_auth_key: { type: 'string' },
        source_url: { type: 'string', description: 'HTTPS URL of the archive or file to copy' },
        path: { type: 'string', description: 'Destination path relative to the upload root, for example site.zip' },
      },
      required: ['upload_url', 'auth_key', 'rest_auth_key', 'source_url', 'path'],
    },
    annotations: { destructiveHint: true },
  },
];

const setting = (env, key) => (env && env[key]) || DEFAULTS[key];
const coreList = (env) =>
  (env?.HOSTINGER_CORE_TOOLS ? env.HOSTINGER_CORE_TOOLS.split(',').map((s) => s.trim()) : CORE).filter((id) => OPS[id]);

function toolFor(id) {
  const op = OPS[id];
  return {
    name: id.replace(/\./g, '_'),
    description: `${op.s}. ${op.d}`.slice(0, 400),
    inputSchema: op.i,
    annotations: {
      readOnlyHint: op.k === 'r',
      destructiveHint: op.k === 'd' || op.k === '$',
      openWorldHint: true,
    },
  };
}

const jsonResponse = (body, status = 200, headers = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json', 'cache-control': 'no-store', ...CORS, ...headers },
  });
const CORS = {
  'access-control-allow-origin': '*',
  'access-control-allow-methods': 'GET, POST, OPTIONS',
  'access-control-allow-headers': 'authorization, content-type, accept, mcp-protocol-version, mcp-session-id',
  'access-control-expose-headers': 'www-authenticate',
};
const toolResult = (t, isError = false) => ({ content: [{ type: 'text', text: t }], ...(isError ? { isError: true } : {}) });

class Unauthorized extends Error {}

function publicOrigin(request, env) {
  if (env?.PUBLIC_URL) return env.PUBLIC_URL.replace(/\/+$/, '');
  const u = new URL(request.url);
  const proto = request.headers.get('x-forwarded-proto') || u.protocol.replace(':', '');
  return `${proto}://${request.headers.get('x-forwarded-host') || u.host}`;
}

function unauthorized(request, env) {
  const meta = `${publicOrigin(request, env)}/.well-known/oauth-protected-resource`;
  return jsonResponse({ error: 'unauthorized', message: 'Sign in to Hostinger to use this server.' }, 401, {
    'www-authenticate': `Bearer realm="hostinger-mcp", resource_metadata="${meta}"`,
  });
}

// ---- Hostinger REST call -------------------------------------------------------------

export function buildRequest(id, params = {}, env) {
  const op = OPS[id];
  const missing = (op.i.required ?? []).filter((k) => params[k] === undefined || params[k] === null);
  if (missing.length) throw new Error(`Missing required argument(s): ${missing.join(', ')}`);
  let path = op.p;
  const query = new URLSearchParams();
  let body;
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined) continue;
    const loc = op.w[key];
    if (loc === 'p') path = path.replace(`{${key}}`, encodeURIComponent(String(value)));
    else if (loc === 'c') query.set(key, Array.isArray(value) ? value.join(',') : String(value));
    else if (loc === 'q') {
      if (Array.isArray(value)) for (const v of value) query.append(`${key}[]`, String(v));
      else query.set(key, String(value));
    } else if (loc === 'B') body = value;
    else if (loc === 'b') (body ??= {})[key] = value;
    else throw new Error(`Unknown argument "${key}". Allowed: ${Object.keys(op.w).join(', ') || 'none'}`);
  }
  if (/\{[^}]+\}/.test(path)) throw new Error(`Unfilled path parameter in ${path}`);
  const qs = query.toString();
  return { method: op.m, url: `${setting(env, 'HOSTINGER_API_URL')}${path}${qs ? `?${qs}` : ''}`, body };
}

async function callOperation(id, params, ctx) {
  const req = buildRequest(id, params, ctx.env);
  const res = await fetch(req.url, {
    method: req.method,
    headers: {
      authorization: ctx.auth,
      accept: 'application/json',
      'user-agent': `${NAME}/${VERSION}`,
      ...(req.body !== undefined ? { 'content-type': 'application/json' } : {}),
    },
    body: req.body !== undefined ? JSON.stringify(req.body) : undefined,
  });
  if (res.status === 401) throw new Unauthorized();
  let out = await res.text();
  const max = Number(setting(ctx.env, 'MAX_RESULT_BYTES'));
  if (out.length > max) {
    out = `${out.slice(0, max)}\n[truncated at ${max} characters. Narrow the request with filters or a smaller per_page.]`;
  }
  if (!res.ok) {
    const retry = res.headers.get('retry-after');
    return toolResult(`Hostinger API ${res.status} on ${req.method} ${OPS[id].p}${retry ? ` (retry after ${retry}s)` : ''}\n${out}`, true);
  }
  return toolResult(out || `{"status":${res.status}}`);
}

// ---- Extra tools ---------------------------------------------------------------------

function suggestOperations(name) {
  const words = String(name).toLowerCase().split(/[^a-z0-9]+/).filter((w) => w.length > 2);
  return Object.keys(OPS)
    .map((id) => [id, words.filter((w) => `${id} ${OPS[id].s}`.toLowerCase().includes(w)).length])
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([id]) => `${id} (${CLASS[OPS[id].k]}): ${OPS[id].s}`);
}

function resolveOperationId(name) {
  if (OPS[name]) return name;
  return Object.keys(OPS).find((id) => id.replace(/\./g, '_') === name);
}

function unknownOperation(name) {
  const near = suggestOperations(name);
  return toolResult(
    `Unknown operation "${name}".${near.length ? ` Closest matches:\n${near.join('\n')}` : ' Read the catalog in the hostinger skill.'}`,
    true,
  );
}

function describeOperation({ operation }) {
  const id = resolveOperationId(operation);
  if (!id) return unknownOperation(operation);
  const op = OPS[id];
  return toolResult(
    JSON.stringify(
      {
        operation: id,
        class: CLASS[op.k],
        needs_confirm: op.k !== 'r',
        deprecated: !!op.x,
        method: op.m,
        path: op.p,
        summary: op.s,
        description: op.d,
        inputSchema: op.i,
      },
      null,
      1,
    ),
  );
}

async function callGated({ operation, params, confirm }, ctx) {
  const id = resolveOperationId(operation);
  if (!id) return unknownOperation(operation);
  const op = OPS[id];
  if (op.k !== 'r' && confirm !== true) {
    return toolResult(
      `${id} is a ${CLASS[op.k]} operation (${op.m} ${op.p}). It did not run. Tell the user the exact target${op.k === '$' ? ' and the price' : ''}, get a yes, then call again with confirm: true.`,
      true,
    );
  }
  return callOperation(id, params ?? {}, ctx);
}

async function setCname({ domain, name, target, ttl }, ctx) {
  const zone = [{ name, type: 'CNAME', ttl: ttl ?? 14400, records: [{ content: target }] }];
  const check = await callOperation('DNS_validateDNSRecordsV1', { domain, overwrite: true, zone }, ctx);
  if (check.isError) return toolResult(`Validation failed. Nothing changed.\n${check.content[0].text}`, true);
  return callOperation('DNS_updateDNSRecordsV1', { domain, overwrite: true, zone }, ctx);
}

function isPrivateIp(ip) {
  const v4 = ip.match(/^(\d+)\.(\d+)\.(\d+)\.(\d+)$/);
  if (v4) {
    const [a, b] = [Number(v4[1]), Number(v4[2])];
    return (
      a === 0 || a === 10 || a === 127 || a >= 224 ||
      (a === 100 && b >= 64 && b <= 127) ||
      (a === 169 && b === 254) ||
      (a === 172 && b >= 16 && b <= 31) ||
      (a === 192 && (b === 168 || b === 0)) ||
      (a === 198 && (b === 18 || b === 19))
    );
  }
  const v6 = ip.toLowerCase();
  const mapped = v6.match(/(\d+\.\d+\.\d+\.\d+)$/);
  if (mapped) return isPrivateIp(mapped[1]);
  // Public IPv6 unicast is 2000::/3. Everything else is loopback, local, mapped or reserved.
  return !/^[23]/.test(v6);
}

// Accepts only an https URL whose host is a DNS name that resolves to public addresses.
// IP literals in any form (dotted, decimal, octal, hex, IPv6) are refused, because the host
// must end in an alphabetic top-level domain. The name is then resolved over DNS-over-HTTPS
// and every address is checked. The check fails closed when resolution fails.
async function publicHttps(value, label, env) {
  let u;
  try {
    u = new URL(value);
  } catch {
    throw new Error(`${label} is not a valid URL`);
  }
  const host = u.hostname.toLowerCase().replace(/\.$/, '');
  const dnsName = /^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/.test(host);
  const reserved = /(^|\.)(localhost|local|internal|lan|home|corp|intranet|test|invalid|example|onion)$/.test(host);
  if (u.protocol !== 'https:' || !dnsName || reserved || u.username || u.password || (u.port && u.port !== '443')) {
    throw new Error(`${label} must be a public https URL with a DNS host name on port 443`);
  }
  const allow = (env?.UPLOAD_ALLOWED_HOSTS || '').split(',').map((h) => h.trim().toLowerCase()).filter(Boolean);
  if (allow.length && !allow.some((h) => host === h || host.endsWith(`.${h}`))) {
    throw new Error(`${label} host is not in UPLOAD_ALLOWED_HOSTS`);
  }
  const addresses = [];
  for (const type of ['A', 'AAAA']) {
    let answer;
    try {
      const res = await fetch(`${setting(env, 'DOH_URL')}?name=${encodeURIComponent(host)}&type=${type}`, {
        headers: { accept: 'application/dns-json' },
      });
      if (!res.ok) throw new Error(String(res.status));
      answer = (await res.json()).Answer ?? [];
    } catch {
      throw new Error(`${label} host could not be resolved, so it was refused`);
    }
    for (const r of answer) if (r.type === 1 || r.type === 28) addresses.push(String(r.data));
  }
  if (!addresses.length || addresses.some(isPrivateIp)) {
    throw new Error(`${label} host does not resolve to public addresses only`);
  }
  return { url: u.toString(), ip: addresses[0] };
}

// Sends a request to a host that passed publicHttps. The connection must go to the checked
// address, or the runtime must be unable to reach private networks. Any other runtime is
// refused, so a DNS record that changes after the check cannot redirect the request.
function fetchChecked(target, init, env) {
  if (typeof env?.pinnedFetch === 'function') return env.pinnedFetch(target.url, init, target.ip);
  if (globalThis.navigator?.userAgent === 'Cloudflare-Workers') return fetch(target.url, init);
  throw new Error(
    'hostinger_upload_from_url is off on this runtime. It runs on Cloudflare Workers, or on Node through node.mjs, which connects to the checked address.',
  );
}

async function uploadFromUrl({ upload_url, auth_key, rest_auth_key, source_url, path }, ctx) {
  const upload = await publicHttps(upload_url, 'upload_url', ctx.env);
  const base = upload.url.replace(/\/+$/, '');
  let next = await publicHttps(source_url, 'source_url', ctx.env);
  if (/(^|\/)\.\.(\/|$)/.test(path) || path.startsWith('/')) throw new Error('path must be relative with no ".." part');
  const max = Number(setting(ctx.env, 'MAX_UPLOAD_BYTES'));
  // Follow redirects by hand so that each hop is checked. A redirect must not reach a private host.
  let source;
  for (let hop = 0; ; hop++) {
    source = await fetchChecked(next, { redirect: 'manual' }, ctx.env);
    if (source.status < 300 || source.status >= 400) break;
    const location = source.headers.get('location');
    if (!location || hop >= 5) return toolResult('source_url redirected too many times or without a location', true);
    next = await publicHttps(new URL(location, next.url).toString(), 'source_url redirect', ctx.env);
  }
  if (!source.ok) return toolResult(`source_url returned ${source.status}`, true);
  const bytes = await source.arrayBuffer();
  if (bytes.byteLength > max) return toolResult(`File is ${bytes.byteLength} bytes. The limit is ${max}.`, true);
  const dest = `${base}/${path.split('/').map(encodeURIComponent).join('/')}?override=true`;
  const tus = { 'x-auth': auth_key, 'x-auth-rest': rest_auth_key, 'tus-resumable': '1.0.0' };
  const destination = { url: dest, ip: upload.ip };
  const create = await fetchChecked(destination, {
    method: 'POST',
    headers: { ...tus, 'upload-length': String(bytes.byteLength), 'upload-offset': '0' },
  }, ctx.env);
  if (create.status !== 201) return toolResult(`TUS create returned ${create.status}: ${(await create.text()).slice(0, 500)}`, true);
  const patch = await fetchChecked(destination, {
    method: 'PATCH',
    headers: { ...tus, 'content-type': 'application/offset+octet-stream', 'upload-offset': '0', 'content-length': String(bytes.byteLength) },
    body: bytes,
  }, ctx.env);
  const offset = Number(patch.headers.get('upload-offset'));
  if (patch.status !== 204 || offset !== bytes.byteLength) {
    return toolResult(`TUS upload returned ${patch.status}, offset ${offset} of ${bytes.byteLength}`, true);
  }
  return toolResult(JSON.stringify({ uploaded: path, bytes: bytes.byteLength }));
}

const EXTRA = { dns_set_cname: setCname, hostinger_describe: describeOperation, hostinger_call: callGated, hostinger_upload_from_url: uploadFromUrl };

// ---- JSON-RPC ------------------------------------------------------------------------

async function rpc(msg, ctx) {
  const { id, method, params } = msg ?? {};
  const ok = (result) => ({ jsonrpc: '2.0', id, result });
  const fail = (code, message) => ({ jsonrpc: '2.0', id: id ?? null, error: { code, message } });
  if (typeof method !== 'string') return fail(-32600, 'Invalid request');
  if (id === undefined) return null; // notification
  switch (method) {
    case 'initialize':
      return ok({
        protocolVersion: PROTOCOLS.includes(params?.protocolVersion) ? params.protocolVersion : PROTOCOLS[0],
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: NAME, version: VERSION },
        instructions: `Hostinger API ${SPEC_VERSION}. The listed tools cover domains, DNS, subdomains and basic hosting. All ${Object.keys(OPS).length} operations run through hostinger_call. The operation names are in the hostinger skill catalog. Call hostinger_describe for one schema before the first use of an operation.`,
      });
    case 'ping':
      return ok({});
    case 'tools/list':
      return ok({ tools: [...coreList(ctx.env).map(toolFor), ...EXTRA_TOOLS] });
    case 'tools/call': {
      const name = params?.name;
      const args = params?.arguments ?? {};
      try {
        if (EXTRA[name]) return ok(await EXTRA[name](args, ctx));
        const opId = coreList(ctx.env).find((c) => c.replace(/\./g, '_') === name);
        if (!opId) return fail(-32602, `Unknown tool "${name}". Use hostinger_call for operations outside the core list.`);
        return ok(await callOperation(opId, args, ctx));
      } catch (e) {
        if (e instanceof Unauthorized) throw e;
        return ok(toolResult(e.message, true));
      }
    }
    default:
      return fail(-32601, `Method not found: ${method}`);
  }
}

// ---- HTTP ----------------------------------------------------------------------------

export async function handle(request, env = {}) {
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, '') || '/';
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });

  if (path.startsWith('/.well-known/oauth-protected-resource')) {
    const suffix = path.slice('/.well-known/oauth-protected-resource'.length);
    return jsonResponse(
      {
        resource: `${publicOrigin(request, env)}${suffix}`,
        authorization_servers: [setting(env, 'HOSTINGER_OAUTH_ISSUER')],
        bearer_methods_supported: ['header'],
        resource_name: 'Hostinger MCP',
      },
      200,
      { 'cache-control': 'public, max-age=3600' },
    );
  }
  if (path === '/.well-known/oauth-authorization-server') {
    // For clients that look for authorization server metadata on the MCP origin.
    try {
      const upstream = await fetch(`${setting(env, 'HOSTINGER_OAUTH_ISSUER')}/.well-known/oauth-authorization-server`);
      return new Response(await upstream.text(), {
        status: upstream.status,
        headers: { 'content-type': 'application/json', 'cache-control': 'public, max-age=3600', ...CORS },
      });
    } catch {
      return jsonResponse({ error: 'bad_gateway', message: 'The authorization server did not answer.' }, 502);
    }
  }
  if (path === '/healthz') {
    return jsonResponse({ ok: true, name: NAME, version: VERSION, spec: SPEC_VERSION, operations: Object.keys(OPS).length });
  }
  if (path !== '/' && path !== '/mcp') return jsonResponse({ error: 'not_found' }, 404);
  if (request.method !== 'POST') return jsonResponse({ error: 'method_not_allowed' }, 405, { allow: 'POST, OPTIONS' });

  const auth = request.headers.get('authorization') || '';
  if (!/^Bearer\s+\S+/i.test(auth)) return unauthorized(request, env);

  let payload;
  try {
    payload = await request.json();
  } catch {
    return jsonResponse({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } }, 400);
  }
  const ctx = { env, auth };
  try {
    if (Array.isArray(payload)) {
      const out = (await Promise.all(payload.map((m) => rpc(m, ctx)))).filter(Boolean);
      return out.length ? jsonResponse(out) : new Response(null, { status: 202, headers: CORS });
    }
    const out = await rpc(payload, ctx);
    return out ? jsonResponse(out) : new Response(null, { status: 202, headers: CORS });
  } catch (e) {
    if (e instanceof Unauthorized) return unauthorized(request, env);
    return jsonResponse({ jsonrpc: '2.0', id: payload?.id ?? null, error: { code: -32603, message: 'Internal error' } }, 500);
  }
}

export default { fetch: (request, env) => handle(request, env) };
