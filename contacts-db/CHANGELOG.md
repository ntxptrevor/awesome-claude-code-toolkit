# Changelog — NTXP Contacts Platform

All dates ISO. See `docs/BLUEPRINT.md` for the live status board and resume flags.

## [Unreleased]

### Added
- **Blueprint & handoff** (`docs/BLUEPRINT.md`) — staged flags + resume context so
  any model can continue mid-build.
- **Layer B — context hooks** (`context/hotlink.py`): `hotlink_text` wraps
  contacts/orgs/emails/phones in blue hotlinks; `contact_context` cards; CLI
  `context`/`hotlink`; MCP `contact_context`/`hotlink_text`.
- **Layers G/H/I — enrichment** (`enrich/*`, `docs/ENRICHMENT.md`): JEV-graded
  candidate pipeline; Gravatar/Libravatar/company-website/public-directory/LinkedIn
  resolvers; out-of-band OSINT (holehe/maigret/GHunt); `confirm_linkedin`
  (field + photo). CLI `enrich *`; MCP enrich tools; migration 0003.
- **Layer E — Workspace sweep** (`collect/workspace.py`): Gmail/Contacts/People/
  Calendar/Drive extractors tagged by channel + data-point date; `ntxp sweep`.
- **Layer F — JEV grading** (`qualify/grader.py`): source·recency·corroboration·
  distance grade + exposure/sync gate; `ntxp qualify`; migration 0002.
- **Layer A — delta reconciliation** (`sync/reconcile.py`, adapters): Lightfield-
  canonical hub; JobTread/QuickBooks/BuildingConnected; change-only; no-echo +
  fan-out; `ntxp reconcile`.
- **Layer C — dual-target DB** (`db/pg.py`): cloud PostgreSQL alongside embedded
  SQLite via `NTXP_DB_URL`; backend-aware migrations; `tsvector`+GIN FTS.
- **Layer D — user-facing page**: NTXP Contacts HTML artifact (banner, VIEW 1/3/5,
  inline edit, labels, hotlink→filter, sortable headers, REPORTS, Settings with
  dark mode + 4 palettes, exports).

### Validation
- Full suite: **51 tests pass** against SQLite and a real PostgreSQL 16 instance.

### In progress / next (see BLUEPRINT flags)
- F1 stateless cloud MCP 2.0 + OAuth + auto-hooks · F2a one-way iOS sync ·
  F2b model council · F2c connector middle-layer · M mirror to NTXP Forge.
