---
name: hostinger
description: "Operate Hostinger through one stateless cloud MCP server with OAuth sign-in. Use for any request about Hostinger or hPanel: domains, DNS records, CNAME, subdomains, websites and hosting, deploys, WordPress, VPS and Docker projects, email, Reach, ecommerce, billing. Also use when a Hostinger call fails or returns 401."
license: MIT
version: 4.0.0
---
# Hostinger

One server, one skill. The server is a cloud MCP endpoint. It keeps no state and needs no local process, no API token, no VPS and no desktop. The MCP client signs in at `auth.hostinger.com` with OAuth and sends the token on each request.

## Tools that are always loaded

| Area | Tools |
|---|---|
| Domains | `domains_getDomainListV1`, `domains_getDomainDetailsV1`, `domains_checkDomainAvailabilityV1`, `domains_updateDomainNameserversV1` |
| DNS and CNAME | `DNS_getDNSRecordsV1`, `DNS_validateDNSRecordsV1`, `DNS_updateDNSRecordsV1`, `DNS_deleteDNSRecordsV1`, `DNS_getDNSSnapshotListV1`, `DNS_restoreDNSSnapshotV1`, `dns_set_cname` |
| Subdomains | `hosting_listWebsiteSubdomainsV1`, `hosting_createWebsiteSubdomainV1`, `hosting_deleteWebsiteSubdomainV1` |
| Hosting | `hosting_listWebsitesV1`, `hosting_listOrdersV1`, `hosting_startWebsiteSetupV1`, `hosting_listWebsiteSetupsV1` |
| Gate | `hostinger_describe`, `hostinger_call`, `hostinger_upload_from_url` |

Use these tools directly. Do not read the catalog for a task that these tools cover.

## All other operations (gated)

The server has 436 operations. Only the tools above are in the tool list. The other operations stay out of context until a task needs them.

1. Read `references/catalog-index.md`. It lists 11 area files.
2. Read the one area file for the task, for example `references/catalog/vps.md`.
3. Call `hostinger_describe` with the operation name. It returns the argument schema.
4. Call `hostinger_call` with `operation` and a flat `params` object.

Do not load more than one area file unless the task crosses areas. Do not guess an operation name. `hostinger_describe` returns the closest names when a name is wrong.

## Confirm before a write

`hostinger_call` runs a read operation immediately. It refuses a write, a delete or a purchase unless `confirm` is `true`. Set `confirm: true` only after the user approved that exact action in this conversation.

| Class in the catalog | Rule |
|---|---|
| SPENDS MONEY | State the item, the price in dollars and the payment method. API prices are integer cents: 1799 is $17.99. Wait for a yes. Never start a purchase from a search. |
| DESTRUCTIVE | Name the exact target (domain, username, VM id). Say what is lost. Wait for a yes. |
| write | Name the target and the change. Wait for a yes. |
| Mail DNS | MX, SPF, DKIM, DMARC and NS changes can stop company mail and still return 200. Use the DNS safe-write playbook each time. |

## Rules for each task

1. Read the current state first: the website list, the zone or the VM list. The server remembers nothing between calls.
2. Get `username` from `hosting_listWebsitesV1`. Get `order_id` from `hosting_listOrdersV1`.
3. Many writes are queued. Poll the matching read operation until the state is complete. Do not send the write again.
4. Verify each change with a second read. For a public change, also check from outside (HTTP request or DNS lookup).
5. Use the playbooks in `references/playbooks.md` for DNS writes, domain search, subdomains, deploys and VPS work.

## Failures

| Symptom | Meaning | Action |
|---|---|---|
| The server asks for sign-in, or returns 401 | No token, or the token expired. Access tokens last 24 minutes and the client refreshes them. | Authorize the `hostinger` server in the client (`/mcp` in Claude Code, connector settings in claude.ai). Do not ask the user for a token. |
| Tool error with 422 | Wrong arguments | Call `hostinger_describe`, correct the arguments, try once more. |
| Tool error with 429 | Rate limit (90 requests in 60 seconds) | Wait for the `retry after` time. Put many TLDs in one call. |
| Tool error with 5xx, two times | Hostinger outage | Stop and report. See `https://statuspage.hostinger.com`. |
| No operation exists for the task | Not an API feature | Say so and name the hPanel page. Do not operate a browser. |
| The tool list shows `search` and `execute`, and no `hostinger_call` | `HOSTINGER_MCP_URL` is not set, so the plugin uses Hostinger's hosted server | Find the operation with `search`, then run it with `execute`. Those names differ from this catalog. Set `HOSTINGER_MCP_URL` to the deployed server to get the tools above. |

## Maintenance

The catalog and the server data come from Hostinger's OpenAPI spec. After a Hostinger API release, run `node build.mjs` in `mcp-servers/hostinger`, run `npm test`, then deploy. The test fails if this skill names an operation that the spec does not contain.
