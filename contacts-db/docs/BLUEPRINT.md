# NTXP Contacts Platform — Blueprint & Resume Flags

> **Handoff protocol.** This file is the single source of truth for the build.
> Any model resuming work reads this first, finds the first task not `DONE`,
> reads its **Resume** notes + linked files, and continues. Update the flag and
> the `CHANGELOG.md` entry when a task changes state. Flags:
> `TODO` · `IN_PROGRESS` · `DONE` · `BLOCKED(reason)`.

Repo: `ntxptrevor/awesome-claude-code-toolkit` · package: `contacts-db/ntxp_contacts`
· branch: `claude/contacts-database-consolidation-7aempk` · PR: #59.
Tests: `cd contacts-db && pytest` (set `NTXP_TEST_PG_URL` for the Postgres suite).

## Vision

One canonical, de-duplicated NTXP contacts database (SQLite local / PostgreSQL
cloud) that every NTXP tool reads and writes; Lightfield is the canonical hub;
all sources reconcile to it on change-deltas; a nightly Workspace sweep collects,
JEV grades, enrichment backfills, and a user-facing page + MCP + hooks expose it.

## Status board

| # | Layer / Feature | Flag | Files |
|---|---|---|---|
| D | User-facing HTML page | DONE | artifact `ntxp-contacts-page.html` |
| C | Dual-target cloud DB (SQLite/Postgres) | DONE | `db/pg.py`, `db/connection.py`, migrations |
| A | Delta two-way reconciliation | DONE | `sync/reconcile.py`, `sync/adapters.py`, `sync/engine.py` |
| E | Nightly Google Workspace sweep | DONE | `collect/workspace.py` |
| F | JEV qualification & grading | DONE | `qualify/grader.py` |
| G/H/I | Enrichment / photos / LinkedIn | DONE | `enrich/*`, `docs/ENRICHMENT.md` |
| B | Tool-agnostic context hooks | DONE | `context/hotlink.py` |
| **F1** | **Stateless cloud MCP 2.0 + OAuth + auto-hooks** | DONE (code) · BLOCKED(deploy) | `remote/*`, `hooks/*` |
| **F2a** | **One-way iOS/iPhone contact sync (CardDAV/vCard)** | DONE (code) · BLOCKED(deploy) | `remote/vcard.py`, `remote/carddav.py` |
| **F2b** | **Mini model council (JEV + cheap LLMs)** | DONE | `council/*`, `docs/COUNCIL.md` |
| **F2c** | **Whitelisted connector middle-layer (Zapier-style)** | TODO | `connectors/` (to build) |
| M | Mirror to NTXP Forge repo `ntxp-contacts` | BLOCKED(repo access) | scratchpad bundle ready |

---

## F1 — Stateless cloud-hosted MCP 2.0 + OAuth + auto-hooks  `DONE (code) · BLOCKED(deploy)`

**Built:** `remote/http_server.py` (stateless streamable-HTTP MCP via FastMCP v1 +
pure-ASGI `AuthMiddleware`), `remote/auth.py` (Google-Workspace OAuth-token verify,
`google|static|none` modes), `remote/maps.py` (Google/Apple maps links),
`remote/plugin.mcp.json` (remote MCP the plugin ships → install = register),
`hooks/contact_context.py` + `hooks/hooks.json` (UserPromptSubmit hook injects
contact cards, blue hotlinks, Maps links, alternate-info preview), `locate_address`
MCP tool, `ntxp serve-http` CLI, `remote` extra (`mcp<2`, uvicorn). Validated:
app builds, `/health` 200, unauthorized `/mcp` 401, hook injects context; 58 tests.
**Remaining (not code):** deploy to the VPS; register the Google OAuth app; set
`NTXP_MCP_URL`/token in the plugin config.

### Original plan (for reference)

**Intent.** An optional, cloud-hosted, stateless **streamable-HTTP MCP** that any
tool/skill/workflow can call for live company-contact access. Clicking it in
plugin settings (or asking for it) offers OAuth re-auth and auto-registers the
MCP in Claude's settings with **zero setup beyond OAuth**. Hooks auto-monitor
conversations for contact queries and inject contact data, blue hyperlinks, live
alternate-info previews, and live Maps location links for addresses.

**Steps.**
1. `remote/http_server.py` — wrap the existing FastMCP tools (`mcp_server.py`)
   with the streamable-HTTP transport; stateless (no server-side session needed;
   all state in the DB). `[ ]`
2. `remote/auth.py` — bearer-token verifier: validate a Google Workspace OAuth
   access token, require `hd == ntxpllc.com`. Pluggable; dev bypass via env. `[ ]`
3. `remote/plugin.mcp.json` — remote MCP entry (`type: http`, `url`,
   `headers: Authorization`) the plugin ships so install = register. `[ ]`
4. `hooks/` — `UserPromptSubmit` hook that detects contact-ish queries and calls
   `context.hotlink`/`enrich` to inject cards, hotlinks, Maps links, alt-info. `[ ]`
5. `remote/maps.py` — `maps_link(address)` → Google Maps URL. `[ ]`
6. Tests for auth gate, maps links, hook payload shaping. `[ ]`

**Resume context.** Reuse `mcp_server.build_server()`. FastMCP ≥1.0 exposes
`.run(transport="streamable-http")` / an ASGI app. Keep it **stateless** so it
scales on the VPS behind the agent proxy. OAuth = token *verification* (not a full
AS) for v1.

**Blockers to flag (not code):** hosting/deploy to the Hostinger VPS; the Google
OAuth app (client id/secret, redirect) under ntxpllc.com.

## F2a — One-way iOS/iPhone contact sync  `DONE (code) · BLOCKED(deploy)`

**Built:** `remote/vcard.py` (vCard 3.0 render + `export_vcards`, exposure-gated),
`remote/carddav.py` (read-only CardDAV: OPTIONS/PROPFIND/REPORT/GET, token-gated,
mounted at `/carddav` by `build_http_app`), `ntxp vcard-export` CLI. Validated:
vCard fields, held-back exclusion, CardDAV multistatus XML + vCard payloads, and
routing/auth through the full app. **Remaining:** deploy (same host as F1) + issue
per-user tokens. 65 tests.

### Original plan (for reference)

**Intent.** OAuth establishes a **one-way** (read-only) contact feed so a new
hire has company contacts on iOS day one.

**Steps.**
1. `remote/vcard.py` — render canonical contacts (exposed/graded only) to vCard
   3.0/4.0, incl. photo + org + title + labels. `[ ]`
2. `remote/carddav.py` — minimal **read-only CardDAV** collection (PROPFIND/REPORT)
   OR a signed `.vcf` subscription URL per user (simpler; iOS "Add Subscribed
   Contacts"-style via CardDAV). Token-scoped, one-way. `[ ]`
3. Respect the exposure gate: never emit `is_exposed=0` contacts. `[ ]`
4. Tests: vCard render + exposure filtering. `[ ]`

**Resume context.** CardDAV read-only is the clean iOS path; a per-user bearer
token grants access. No write-back (one-way by design).

**Blockers:** hosting + per-user token issuance (ties to F1 auth).

## F2b — Mini model council (JEV + cheap LLMs)  `DONE`

**Built:** `council/` — `JEVJudge` (free, deterministic, default decider) +
key-gated OpenAI-compatible `DeepSeekJudge`/`GrokJudge`/`OpenAIJudge`; router
escalates to the cheapest available judge only when JEV is uncertain, then
weighted-votes with provenance. Env-overridable models/endpoints (near-zero
maintenance). `ntxp council` CLI; `council_decide` MCP tool; `docs/COUNCIL.md`
cost/capability table. Runs for free with no keys. 70 tests. **Live LLM voting
needs API keys** (framework + JEV path need none).

### Original plan (for reference)

**Intent.** Near-zero-cost council that divides qualification/decision tasks
across JEV (deterministic, free) + cheap LLMs (Grok, DeepSeek, others). Try the
OpenAI Responses/decisions API if the feature set fits.

**Steps.**
1. Check existing `ntxp-model-council` skill; integrate, don't duplicate. `[ ]`
2. `council/base.py` — `Judge` protocol (`decide(task) -> {choice, confidence,
   cost}`), registry, cost table. `[ ]`
3. `council/judges.py` — `JEVJudge` (free default, wraps `qualify.score`);
   `GrokJudge`, `DeepSeekJudge`, `OpenAIJudge` — activate only when API keys
   present; else skipped. `[ ]`
4. `council/router.py` — route by task type + cost cap; cheapest-capable first,
   escalate on low confidence; majority/weighted vote. `[ ]`
5. A tiny bench harness + a cost/capability table in `docs/COUNCIL.md`. `[ ]`
6. Tests: routing, JEV-only path works with no keys, vote logic. `[ ]`

**Resume context.** Keep JEV as the zero-cost default so the council runs with no
keys. LLM judges are optional, key-gated, stateless HTTP calls.

**Blockers:** API keys for live LLM testing (framework + JEV path need none).

## F2c — Whitelisted connector middle-layer  `TODO`

**Intent.** A Zapier-like whitelisted layer so users securely connect accounts to
scrape / add / sync contacts across many services.

**Steps.**
1. `connectors/base.py` — `Connector` protocol (`list_contacts`, `push_contact`),
   allowlist of permitted services, per-user auth handle (token ref, never
   secrets in repo). `[ ]`
2. `connectors/zapier.py` — adapter over the Zapier MCP (`mcp__Zapier__*`) as the
   real middle layer; map Zapier actions → canonical records via existing
   adapters/`reconcile`. `[ ]`
3. Document the allowlist + security model in `docs/CONNECTORS.md`. `[ ]`
4. Tests: allowlist enforcement, canonical mapping. `[ ]`

**Resume context.** Zapier MCP is available in-session (`mcp__Zapier__*`). Live
workflow creation is outward-facing — build the framework + mapping now; gate
actual workflow creation on explicit user go-ahead.

**Blockers:** user's Zapier account auth; explicit approval before creating live
workflows.

## M — Mirror to NTXP Forge `ntxp-contacts`  `BLOCKED(repo access)`

Standalone installable plugin bundle is prepared (scratchpad `ntxp-contacts/`:
`.claude-plugin`, `.mcp.json`, `skills/`, `commands/`, `install.sh`, `pysrc/`).
**Blocked:** this session's GitHub scope is only `ntxptrevor/awesome-claude-code-toolkit`;
creating/pushing a new repo in NTXP Forge needs that repo added to scope (via
`add_repo`/access grant). Once granted: push the bundle, keep this `contacts-db/`
as upstream, mirror on release.

---

## Changelog pointer
See `CHANGELOG.md` for dated, shipped entries. Keep it in lockstep with the flags
above.
