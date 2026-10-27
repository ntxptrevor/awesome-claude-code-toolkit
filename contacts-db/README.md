# NTXP Contacts Database

One **master, de-duplicated contacts database** for all NTXP tools. Consolidates
contact exports from multiple systems into a single SQLite file that any tool
can query, update independently, and keep in sync with external CRMs.

- **Single source of truth** — one DB: embedded SQLite (`~/.ntxp/contacts.db`)
  for local/CLI use, or a cloud **PostgreSQL** canonical store (set `NTXP_DB_URL`)
  that the web UI and sync services share. Same engine, same schema, same CLI.
- **Idempotent imports** — re-running a source import never duplicates; changed
  rows update in place, unchanged rows are skipped.
- **De-duplication with provenance** — people/orgs are matched across sources;
  every canonical record traces back to its raw source rows.
- **Three access layers** over one core library: Python API, `ntxp` CLI, and an
  MCP server so Claude-based NTXP tools can query it directly.
- **Bi-directional CRM sync** — pluggable adapters (REST or MCP-mediated) with
  field-level last-write-wins and a `master_wins` allowlist.

> **Privacy:** this directory ships **code only**. Real contact data (the source
> files and the built `.db`) is gitignored and never committed.

## Install

```bash
pip install -e contacts-db                       # core
pip install -e "contacts-db[mcp,ocr,postgres,dev]"  # + MCP, OCR, Postgres, tests
```

## Backends: local SQLite vs. cloud PostgreSQL

The store is **dual-target**. By default it uses an embedded SQLite file. Point
it at Postgres by setting `NTXP_DB_URL` (precedence: a `postgres://` value passed
to `--db` or the API > `NTXP_DB_URL` > SQLite via `NTXP_DB_PATH`/default):

```bash
export NTXP_DB_URL='postgresql://ntxp:••••@db.internal:5432/ntxp_contacts'
ntxp init         # applies the Postgres schema (0001_init.postgres.sql)
ntxp stats
```

Everything else is identical — imports, dedup, FTS search, prune, and sync all
run unchanged. Under the hood the repository is authored in the SQLite idiom and
a thin translator rewrites it for Postgres (placeholders, `datetime('now')`,
`GROUP_CONCAT`→`string_agg`, identity-key `RETURNING`), and full-text search uses
a generated `tsvector` + GIN index in place of FTS5.

**Deploying the cloud canonical DB (Hostinger VPS):** provision PostgreSQL on the
existing VPS (near-zero marginal cost, private, reliable), create a database and
a least-privilege role, then run `ntxp init` once with `NTXP_DB_URL` set to that
DSN. The web UI and the sync services read/write the same database. Keep the DSN
in the NTXP secrets vault — never commit it.

> Run the Postgres-backend tests against a reachable instance with
> `NTXP_TEST_PG_URL=<dsn> pytest tests/test_postgres.py` (they're skipped
> otherwise).

## Quick start

```bash
ntxp init                                   # create DB + run migrations
ntxp import all --all /path/to/source/files # load every spreadsheet source
ntxp stats                                  # entity counts + per-source provenance
ntxp query "Vaden"                          # full-text search
ntxp export --format csv --out contacts.csv
ntxp prune --source tips --keep-states TX,OK --dry-run   # preview a regional cleanup
ntxp prune --source tips --keep-states TX,OK             # tombstone members outside TX/OK (reversible)
```

### Sources & loaders

| Source key | File | Loader |
|---|---|---|
| `tips` | TIPS member export (`.xlsx`) | `loaders/tips.py` |
| `buildingconnectd` | BuildingConnected bid invites (`.xlsx`) | `loaders/buildingconnectd.py` |
| `approved_subs` | Approved subcontractors (`.xls`) | `loaders/approved_subs.py` |
| `luncheon` | Event registrants (`.xls`) | `loaders/luncheon.py` |
| `cjp_pdf` | Certified JOC Professional holders (scanned PDF) | `loaders/cjp_pdf.py` |

### CJP scanned PDF (OCR)

The CJP holders file is a scanned image with no text layer, so it is extracted,
OCR'd, and **quarantined for review** before touching canonical tables:

```bash
ntxp extract-cjp All_CJP_Holders.pdf cjp.jsonl   # writes page images to OCR
# OCR the images -> write {full_name,company,...,confidence} JSONL rows
ntxp import cjp_pdf cjp.jsonl                     # routes rows into staging
ntxp staging list                                 # review
ntxp staging promote --all-above 0.9              # promote high-confidence rows
```

## Architecture

```
ntxp_contacts/
  config.py            thresholds, source-trust ranking, master-wins fields
  normalize.py         phones (E.164), emails, zips, dates, names, org names
  model.py             CanonicalRecord dataclasses
  db/                  connection (WAL/FK), repository (all SQL), migrations
  resolve/             blocking + weighted scoring + reversible merges
  loaders/             one per source + the idempotent import pipeline
  sync/                CrmAdapter interface, engine, adapters (REST + MCP)
  cli.py               the `ntxp` command
  mcp_server.py        FastMCP tools (search/get/upsert/export/sync)
```

### How dedup works

Normalize → block → score → decide. Email (when valid) is a deterministic merge
key; otherwise candidates are blocked by last name / shared org and scored on
`0.45*name + 0.30*org + 0.20*phone + 0.05*state`. Scores `>= 0.85` auto-merge;
`0.65–0.85` are flagged for review (`ntxp dedup review`); merges are reversible
(tombstones, never hard-deletes).

### Sync

`ntxp sync push --system quo --dry-run` prints a plan with no writes. REST
adapters run headless; MCP-only CRMs (e.g. Lightfield) are driven by an agent
through the MCP server's `sync_plan` / `record_sync_result` tools. Conflict
policy is field-level last-write-wins with a configurable `master_wins`
allowlist so NTXP-curated fields are never clobbered.

### Delta reconciliation (Lightfield-canonical hub)

**Lightfield is the canonical first source** (`config.CANONICAL_SOURCE`): every
system reconciles back to it. Adapters ship for **Lightfield, JobTread,
QuickBooks, BuildingConnected** (and Quo). The agent pulls records from a system
(via its MCP/REST tool), dumps them to JSON, then:

```bash
ntxp reconcile --system jobtread pulled.json            # read-only delta plan
ntxp reconcile --system jobtread pulled.json --apply    # enrich canonical DB
```

or, over MCP, the `reconcile_plan` / `reconcile_apply` tools. The plan classifies
each record as **create / link / update / conflict / unchanged** and lists the
exact fields that disagree with canonical. It's **change-only**: a record whose
remote payload hash already matches the stored link is skipped. `apply` writes
**only to the local canonical store** — never to the remote CRM — linking
`external_ids` and recording provenance. Applied pulls are tagged
`pull:<system>` in the change-log, so they **fan out** to the *other* systems'
push plans but never **echo** back to the system they came from. Field conflicts
are surfaced for review; lower-ranked systems never overwrite a Lightfield value
(`config.SYSTEM_PRECEDENCE`).

## Configuration

| Env var | Purpose | Default |
|---|---|---|
| `NTXP_DB_PATH` | SQLite DB file location | `~/.ntxp/contacts.db` |
| `NTXP_DB_URL` | PostgreSQL DSN (cloud canonical store); overrides SQLite | _(unset)_ |

## Tests

```bash
pytest contacts-db/tests
```
