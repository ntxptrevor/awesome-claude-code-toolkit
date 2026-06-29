---
name: canonical-project-model
description: Normalizes the verbatim project-intake dossier (which Mistral OCR4 produced) into the Canonical Project Record - one reusable, CSI/UniFormat-aligned, provenance-carrying source of truth covering project identity, scope, quantity takeoff, estimate/SOV, budget, trades, subcontractors, sub-bid log, RFI/submittal logs, safety plan, logistics plan, schedule, and requirements. Uses parallel section agents and a deterministic assembler; built for downstream estimating/PM tools to pull from - it organizes and structures, it never prices, levels, or decides.
---

# Canonical Project Model — the source-of-truth layer

The normalization node of the `construction-doc-pipeline`. It sits between the
verbatim **project-intake dossier** (which `mistral-ocr4` extracted) and the
reasoning tools, and produces the **Canonical Project Record (CPR)** — one stable,
machine-readable structure that every estimating and project-management tool pulls
from instead of re-parsing documents.

**The one rule that shapes everything (inherited from the extraction layer):**
> **OCR4 extracts. project-intake gathers. this layer normalizes. downstream reasons.**
> Map to standards, convert units, dedup entities, link references, carry provenance.
> Never price, level bids, validate a low bid, judge compliance, score, or pick a
> winner — that is `vendor-bid-leveling`, `rfp-analysis`, `invoice-reconciliation`,
> `submittal-review`, and the estimating tools' job. A value enters the model only if
> a document stated it; empty structured slots are left for the tools that fill them.

## Why this layer exists

`project-intake` deliberately stops at verbatim extraction with provenance and defers
"cross-document dedup/normalization." Without a normalization layer, every downstream
tool re-derives the same structure from raw extracts — slow, inconsistent, and
error-prone. This skill produces that structure **once**, so pricing, budgeting,
scheduling, buyout, and compliance tools share a single source of truth and the same
facts spread to every party.

## Inputs — what you read

The finished dossier at `projects/<slug>/` (never re-OCR):

- `handoff.json` — the intake contract (status, document inventory, extract paths).
- `extracts/*.json` — products, schedules, contacts, scope-items, requirements
  (each record already carries `_doc`, page, bbox).
- `extracts/product-tables.csv` — every table block with page + bbox.
- `_raw/<doc>.ocr.json` — the raw OCR4 envelopes, for anything the extracts missed.
- `project.json` — resolved project identity.

## The Canonical Project Record (output)

A root `canonical-model.json` plus one file per section under `model/sections/`,
each conforming to a fixed schema in the plugin's `schemas/` folder:

| Section | What it holds |
| --- | --- |
| `project_identity` | who/what/where, delivery method, contract type, key dates, bonding/insurance/wage, **JOC/IDIQ** block (UPB, coefficient, NTE, task order) |
| `scope` | master scope register, CSI-coded — the rows everything else maps to; inclusions/exclusions/alternates/allowances |
| `quantity_takeoff` | measured/stated quantities by CSI + UOM + location/assembly |
| `estimate_sov` | estimate cost lines (Material/Labor/Equipment/Subcontract split), markup ladder, **AIA G703 SOV**, JOC line-item proposal |
| `budget` | cost-code cost plan / buyout targets |
| `trades` | trade / bid-package breakdown |
| `subcontractors` | deduped subs & suppliers directory — the party table other sections reference by `party_id` |
| `sub_bid_log` | bid tab of subcontractor bids received per trade |
| `rfi_log` | RFI register |
| `submittal_log` | submittal register |
| `safety_plan` | site-specific safety inputs (hazards, required programs, PPE, emergency) |
| `logistics_plan` | site logistics inputs (access, staging, hoisting, phasing, controls) |
| `schedule` | milestones & key dates |
| `requirements` | binding requirements, evaluation criteria, addenda (verbatim) |

The root carries `counts`, `confidence` (overall + per section), `normalization_log`,
`conflicts`, `needs_human_review`, and `next_consumers`. A human-readable
`project-record.md` is rendered alongside, and `model-handoff.json` is the downstream
contract. PMs/admins can read it; it is **built for tools**, not operated by people.

## Normalization rules (what "structuring" means here)

- **Classification.** Tag every item with CSI MasterFormat division/section, and
  UniFormat where system-level rollups help. Map to the firm's cost code when evident.
- **Units.** Normalize `uom` to the canonical set (EA, LF, SF, SY, CY, TON, LS, HR…)
  and record the conversion in `normalization.actions`; keep the original in `as_written`.
- **Entities.** Dedup companies/people into one `party_id` in `subcontractors`; every
  other section references that id rather than repeating contact details.
- **Verbatim + provenance.** Keep binding text word-for-word; carry `source_doc`,
  page, bbox, and confidence on every record. Low confidence is flagged, never dropped.
- **Conflicts surface, never resolve.** When two documents disagree on one fact,
  record both with provenance in `conflicts` / `needs_human_review`.
- **Never invent.** No price, quantity, date, or party that no document stated.

## Parallel processing (default to it)

Sections are independent, so fan out:

- Reconcile the **`subcontractors`** directory first (or as a short reduce step) so the
  other sections can reference parties by `party_id`.
- Launch one **section normalizer per remaining section concurrently** — each reads the
  dossier and writes its own `model/sections/<section>.json`. Keep per-section work
  independent; the only shared state is the party table and the final assembly.
- **Assembly is the single barrier:** `scripts/assemble_model.py` validates each
  section against its schema, stitches `canonical-model.json`, renders
  `project-record.md`, and emits `model-handoff.json` — deterministically, no network.

## Cross-references

- `mistral-ocr4` — extraction layer (upstream of intake).
- `project-intake` (plugin) — builds the dossier this skill consumes.
- `construction-doc-pipeline` — the orchestration spine; this is its normalization node.
- `rfp-analysis`, `vendor-bid-leveling`, `invoice-reconciliation`, `submittal-review`
  — downstream reasoning tools that PULL from the canonical sections.
- `lean-pm-judgment` — applied downstream, not here.

## Anti-patterns

- Re-OCR'ing or re-parsing documents the dossier already extracted.
- Reasoning in this layer: leveling bids, validating the low bid, judging compliance,
  pricing, scoring, recommending an award.
- Inventing a value (price/quantity/date/party) not present in any document.
- Dropping provenance, or "fixing" a value silently instead of recording a
  `normalization` action.
- Leaving cross-document disagreements silently resolved instead of in `conflicts`.
- Duplicating contact details across sections instead of referencing a `party_id`.
- Faking absent sections instead of omitting them.

## Checklist

- [ ] Consumed the existing dossier; no re-OCR.
- [ ] Subcontractor directory deduped; sections reference parties by `party_id`.
- [ ] Every item CSI/UniFormat-tagged where applicable; units normalized with notes.
- [ ] Verbatim text + provenance + confidence on every record.
- [ ] Conflicts and low-confidence values surfaced in `needs_human_review`.
- [ ] Sections normalized in parallel; assembly run once as the barrier.
- [ ] `canonical-model.json`, `project-record.md`, and `model-handoff.json` written
      with accurate status, counts, and `next_step`.
- [ ] No reasoning performed here — structure handed to the downstream tools.
