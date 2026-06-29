# /canonical-project-model:structure

Normalize a project-intake dossier into the **Canonical Project Record (CPR)** —
the single, reusable, machine-readable source of truth every downstream estimating
and project-management tool pulls from. Reasoning (reading the dossier and mapping
each domain to its section schema) runs as **parallel section-normalizer agents**;
a deterministic script validates and assembles the result.

## Usage

```
/canonical-project-model:structure <projects/<slug>  |  path/to/handoff.json>
```

If given a `handoff.json`, its `dossier_dir` is used. The dossier must already
exist (run `/project-intake:ingest` first). This step never re-OCRs.

## Steps

1. **Locate the dossier.** Read `projects/<slug>/handoff.json` and its
   `extracts/*.json`, `_raw/<doc>.ocr.json`, and `project.json`. These verbatim
   extracts (with provenance) are the only input — extraction already happened.
2. **Fan out one normalizer per section, in parallel.** Launch a
   `section-normalizer` agent for each canonical section (project_identity, scope,
   quantity_takeoff, estimate_sov, budget, trades, subcontractors, sub_bid_log,
   rfi_log, submittal_log, safety_plan, logistics_plan, schedule, requirements).
   Each agent reads the relevant extracts, maps them to CSI MasterFormat / UniFormat,
   normalizes units and entities, preserves verbatim text + provenance, and writes
   `projects/<slug>/model/sections/<section>.json` conforming to
   `schemas/<section>.schema.json`. Sections are independent — they all run at once.
   The **subcontractors** agent should finish first (or be reconciled first) so other
   agents can reference parties by `party_id`; if run fully in parallel, the
   orchestrator reconciles party ids in a short reduce step.
3. **Record cross-document findings.** Where two documents disagree on the same fact,
   write both into `model/sections/_meta.json` under `conflicts` (do not silently
   pick one). Put cross-section normalization notes in `normalization_log` and any
   manual-attention items in `needs_human_review`.
4. **Assemble.** Run `scripts/assemble_model.py --dossier projects/<slug>`. It
   validates each section against its schema, stitches `canonical-model.json`
   (the source of truth), renders `project-record.md` (human-readable), and emits
   `model-handoff.json` with status, counts, confidence, and `next_step`.

## Running the assembler directly

```bash
# Plan only — shows which section files are present (no work, no network)
python plugins/canonical-project-model/scripts/assemble_model.py --dossier projects/lincoln-clinic-ti --dry-run

# Assemble after the normalizer agents have written model/sections/*.json
python plugins/canonical-project-model/scripts/assemble_model.py \
  --dossier projects/lincoln-clinic-ti --generated-at "$(date -u +%FT%TZ)"
```

`--no-embed` references sections by relative path instead of embedding them inline
in `canonical-model.json`; `--model-version N` bumps the revision as addenda arrive.

## Rules

- **Normalize, never reason.** Map to CSI/UniFormat, convert units, dedup entities,
  link references, carry provenance. Do **not** price, level bids, validate the low
  bid, judge compliance, or pick a winner — those are downstream skills
  (`vendor-bid-leveling`, `rfp-analysis`, `invoice-reconciliation`, estimating).
- **Never invent values.** A price/quantity/date appears in the model only if it was
  in a document (verbatim preserved); empty structured slots are left for the tools
  that fill them.
- **Provenance on everything.** Every value carries `source_doc`, page, bbox, and
  confidence from the OCR4 envelope so any consumer can cite and re-verify.
- **Conflicts surface, never resolve silently.** Disagreements go to `conflicts` /
  `needs_human_review`.
- **Idempotent.** Re-running updates the same `projects/<slug>/model/`.
- Always emit `model-handoff.json`, even on partial/failed assembly (status reflects it).
