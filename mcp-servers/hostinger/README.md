# Hostinger MCP server

A stateless MCP server for the full Hostinger API. One file of server code, zero dependencies, generated from Hostinger's OpenAPI spec (2.13.1, 436 operations).

| Property | How |
|---|---|
| Stateless | No session, no database, no token storage. Each request carries its own bearer token. |
| Cloud | One fetch handler. Runs on Cloudflare Workers, Vercel Edge, Deno Deploy, or Node 18+. |
| No dependencies | No npm packages at run time. `package.json` has no `dependencies`. |
| OAuth | The server is an OAuth protected resource. It names `https://auth.hostinger.com` as the authorization server. The MCP client registers itself, runs PKCE in the browser, and refreshes the token. |
| All operations | 17 core operations and 4 gate tools are listed. `hostinger_call` runs any of the 436 operations. |

## Tools

| Tool | Purpose |
|---|---|
| 17 core operations | Domains, DNS, subdomains, basic hosting. Named by operationId. See `CORE` in `src/server.mjs`. |
| `dns_set_cname` | Validate, then write one CNAME record. |
| `hostinger_describe` | Schema of one operation. Suggests names on a miss. |
| `hostinger_call` | Run any operation. A write, delete or purchase needs `confirm: true`. |
| `hostinger_upload_from_url` | Copy a file from an HTTPS URL to Hostinger file storage (TUS). |

The tool list is 19 KB. A list of all 436 operations with schemas is about 390 KB.

## Deploy

Cloudflare Workers:

```bash
npx wrangler deploy
```

Node (any host):

```bash
PORT=8787 node node.mjs
```

Then set the client URL to `https://<host>/mcp`.

## Configuration

All variables are optional.

| Variable | Default | Purpose |
|---|---|---|
| `PUBLIC_URL` | From the request | Public origin, when the server is behind a proxy or a custom domain |
| `HOSTINGER_CORE_TOOLS` | `CORE` list | Comma list of operationIds to keep in the tool list |
| `HOSTINGER_API_URL` | `https://developers.hostinger.com` | REST API base |
| `HOSTINGER_OAUTH_ISSUER` | `https://auth.hostinger.com` | Authorization server |
| `MAX_RESULT_BYTES` | `120000` | Limit for one tool result |
| `MAX_UPLOAD_BYTES` | `52428800` | Limit for `hostinger_upload_from_url` |
| `UPLOAD_ALLOWED_HOSTS` | Not set | Comma list of host suffixes that `hostinger_upload_from_url` can read from and write to |
| `DOH_URL` | `https://cloudflare-dns.com/dns-query` | DNS-over-HTTPS resolver for the upload host check |

## Endpoints

| Path | Purpose |
|---|---|
| `POST /mcp` or `POST /` | MCP Streamable HTTP, JSON responses |
| `GET /.well-known/oauth-protected-resource` | RFC 9728 metadata |
| `GET /.well-known/oauth-authorization-server` | Copy of Hostinger's metadata, for older clients |
| `GET /healthz` | Version, spec version, operation count |

## Authentication flow

1. The client sends a request with no token. The server returns 401 and a `WWW-Authenticate` header with the metadata URL.
2. The client reads the metadata, registers at `auth.hostinger.com`, and opens the browser for consent.
3. The client sends `Authorization: Bearer <token>`. The server forwards the header to the Hostinger REST API.
4. When Hostinger returns 401, the server returns 401, and the client refreshes the token.

A Hostinger API token from hPanel also works as the bearer value, for a client that sets a fixed header.

## Update for a new Hostinger API release

```bash
node build.mjs
```

```bash
npm test
```

`build.mjs` fetches the live spec and writes `src/catalog.mjs` and the skill catalog in `plugins/ntxp-hostinger`.

## Upload host check

`hostinger_upload_from_url` makes the server fetch a URL, so each URL and each redirect hop passes these checks:

1. The scheme is `https`, the port is 443, and the URL has no user name.
2. The host is a DNS name with an alphabetic top-level domain. An IP address in any form (dotted, decimal, octal, hex, IPv6) is refused.
3. The name is resolved over DNS-over-HTTPS. Every A and AAAA address must be public. A failed lookup refuses the URL.
4. When `UPLOAD_ALLOWED_HOSTS` is set, the host must match one suffix in the list.

One limit remains: the runtime resolves the name again for the fetch, so a DNS record that changes between the check and the fetch is not caught. Cloudflare Workers cannot reach private addresses, which closes that gap. On a Node host inside a private network, set `UPLOAD_ALLOWED_HOSTS`.
