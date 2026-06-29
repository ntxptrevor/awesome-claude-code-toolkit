# canonical-project-model

The **normalization layer** of the `construction-doc-intelligence` pipeline. It takes
the verbatim **project dossier** that `project-intake` built (from Mistral OCR4
extraction) and turns it into the **Canonical Project Record (CPR)** — one reusable,
CSI/UniFormat-aligned, provenance-carrying source of truth that every downstream
estimating and project-management tool pulls from instead of re-parsing documents.

Separation of concerns (dependencies point downward only):

```
mistral-ocr4 (extraction)
      │
      ▼
project-intake  ──▶  projects/<slug>/  (verbatim dossier, with provenance)
      │
      ▼
canonical-project-model (this plugin)  ──▶  projects/<slug>/model/  (the CPR — one source of truth)
      │
      ▼
estimating · bid-leveling · scheduling · buyout · RFI/submittal · safety · logistics  (consumers PULL from the CPR)
```

- **OCR4 extracts. project-intake gathers. this plugin normalizes. downstream reasons.**
  This layer maps to standards, converts units, dedups entities, links references, and
  carries provenance. It **never** prices, levels bids, validates a low bid, judges
  compliance, or picks a winner — that reasoning belongs to the domain skills.

## What it produces

```
projects/<slug>/model/
  canonical-model.json      # THE source of truth (schema: schemas/canonical-model.schema.json)
  sections/
    project_identity.json   # who/what/where, delivery & contract, key dates, bonding/wage, JOC/IDIQ block
    scope.json              # master scope register, CSI-coded (rows everything else maps to)
    quantity_takeoff.json   # measured/stated quantities by CSI + UOM + location
    estimate_sov.json       # estimate cost lines (M/L/E/S split), markups, AIA G703 SOV, JOC line items
    budget.json             # cost-code cost plan / buyout targets
    trades.json             # trade / bid-package breakdown
    subcontractors.json     # deduped subs & suppliers directory (the party table others reference)
    sub_bid_log.json        # bid tab of subcontractor bids received per trade
    rfi_log.json            # RFI register
    submittal_log.json      # submittal register
    safety_plan.json        # site-specific safety inputs (hazards, programs, PPE, emergency)
    logistics_plan.json     # site logistics inputs (access, staging, hoisting, phasing, controls)
    schedule.json           # milestones & key dates
    requirements.json       # binding requirements, evaluation criteria, addenda (verbatim)
    _meta.json              # cross-document conflicts, normalization log, review flags
  project-record.md         # human-readable projection of the CPR
  model-handoff.json        # the downstream contract (schema: schemas/model-handoff.schema.json)
```

Every record carries provenance (`source_doc`, page, bbox, confidence) so any
consumer can cite and re-verify. Low-confidence values, unresolved conflicts, and
invalid sections land in `model-handoff.json.needs_human_review`.

## How it works

1. **Reasoning is parallel.** The `model-orchestrator` agent fans out one
   `section-normalizer` subagent per section; they run concurrently, each reading the
   dossier extracts and writing one schema-conforming file under `model/sections/`.
   The subcontractor directory is reconciled first so other sections reference parties
   by `party_id`.
2. **Assembly is deterministic.** `scripts/assemble_model.py` (stdlib-only, no network)
   validates each section against its schema, stitches `canonical-model.json`, renders
   `project-record.md`, and emits `model-handoff.json`. Mirrors `project-intake`'s
   build script: agents reason, the script only validates, stitches, and writes.

## Run it

```bash
# Plan only — shows which section files are present (no work, no network)
python scripts/assemble_model.py --dossier projects/lincoln-clinic-ti --dry-run

# Assemble after the normalizer agents wrote model/sections/*.json
python scripts/assemble_model.py --dossier projects/lincoln-clinic-ti --generated-at "$(date -u +%FT%TZ)"
```

Key flags: `--dossier` (the project-intake folder), `--sections` (override the
sections dir), `--out` (override the output dir), `--model-version N` (bump the
revision as addenda arrive), `--no-embed` (reference sections by path instead of
embedding inline), `--dry-run`.

Or drive the whole thing from chat / an agent loop with `/canonical-project-model:structure`.

## Standards it aligns to

- **CSI MasterFormat 2020** — scope, procurement, cost codes.
- **CSI UniFormat II** — systems/assemblies for conceptual & QTO rollups.
- **AIA G702/G703** — Schedule of Values / Application for Payment structure.
- **JOC / IDIQ** — unit price book (e.g. RSMeans/Gordian) line references, coefficient,
  NTE, task-order identity.

## Boundaries

Normalize and organize — never reason. No bid leveling, low-bid validation, pricing,
compliance calls, scoring, or award recommendations here; those are
`vendor-bid-leveling`, `rfp-analysis`, `invoice-reconciliation`, `submittal-review`,
and the estimating tools that consume this record. Never invent a value not in a
document. Never re-OCR — extraction is `mistral-ocr4`'s job.
