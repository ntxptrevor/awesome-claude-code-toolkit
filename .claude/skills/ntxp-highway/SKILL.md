---
name: "NTXP Highway"
description: "High-speed skill routing and orchestration layer for NTXP. Routes tasks to the optimal skill, model, or agent based on intent classification, cost tier, and latency budget. Works alongside Model Council and Model Reps to form the NTXP intelligence stack. Use when a task could be handled by multiple skills and needs fast, automatic routing — or when building multi-skill workflows that chain outputs across the NTXP ecosystem."
---

# NTXP Highway

## What This Skill Does

Highway is the fast-lane router for NTXP's skill ecosystem. When a task arrives, Highway classifies intent, checks the skill registry, evaluates cost/latency tiers, and dispatches to the best handler — all before the user waits for a response. It replaces manual skill invocation with automatic, intelligent routing.

## Shared Conventions

Highway follows the NTXP shared conventions defined in the NTXP IPDM skill. Key references:

| Convention | Source |
|-----------|--------|
| File paths | `.ntxp/ipdm/` (project data), `.ntxp/coda/` (links), `.ntxp/highway/` (routing) |
| Platform keys | `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot` |
| Credential chain | `ntxp-id` → `ntxp-secrets-vault` → never hardcode |
| Model routing | Read `.ntxp/ipdm/model-council.yaml` → call `ntxp-model-council` if missing → log to `.ntxp/highway/routing-log.jsonl` |
| Knowledge base | Search `.ntxp/ipdm/` first → save outputs back → register links in `.ntxp/coda/` |
| Skill bindings | Declared in `.ntxp/ipdm/skill-config.yaml` — Highway reads this at routing time |

## When to Use

- A task could be handled by multiple NTXP skills (estimating vs. takeoff vs. ITB)
- Building multi-step workflows that chain skill outputs
- Need to route between Model Council models based on task complexity
- Want automatic fallback when a primary skill or model is unavailable
- Optimizing cost by sending simple tasks to cheaper tiers

## Architecture

```
User Request
    |
    v
+------------------+
|   NTXP Highway   |  <-- Intent classification + routing
+------------------+
    |         |         |
    v         v         v
 Tier 1    Tier 2    Tier 3
 (Local)   (Haiku)   (Opus/Sonnet)
    |         |         |
    v         v         v
+-------+ +-------+ +----------+
| Skill | | Skill | | Model    |
| Cache | | Route | | Council  |
+-------+ +-------+ +----------+
    |         |         |
    v         v         v
+--------------------------------------+
|  .ntxp/ipdm/  (shared knowledge)    |
|  .ntxp/coda/  (link registry)       |
+--------------------------------------+
```

## Routing Table

This is the canonical routing table. Auto-deploy bootstraps `.ntxp/highway/config.yaml` from this. All 10 routes must appear in both places.

| Intent Pattern | Primary Skill | Fallback | Tier |
|---------------|---------------|----------|------|
| `estimate\|price\|cost\|budget` | ntxp-estimating | rsmeans-estimate-generator | 3 |
| `takeoff\|quantity\|measure` | ntxp-quantity-takeoff | demolition-takeoff | 3 |
| `bid\|ITB\|solicit` | ntxp-project-itb-brief | itb-generator | 2 |
| `folder\|file\|organize\|drive` | ntxp-folder-system | ntxp-folder-structure | 1 |
| `schedule\|SOV\|pay app\|billing` | dallas-isd-sov-payapp-review | estimating | 3 |
| `submittal\|RFI` | ntxp-submittal-command | specs-skill | 2 |
| `credential\|key\|secret\|token` | ntxp-secrets-vault | — | 1 |
| `markup\|redline\|plan` | ntxp-pdf-markups-and-redlines | apply-construction-markups | 2 |
| `project setup\|init\|deploy` | auto-deploy-claude-flow | init | 1 |
| `model\|council\|AI\|routing` | ntxp-model-council | — | 2 |

## Model Selection at Routing Time

Highway integrates with Model Council for model-level routing:

1. **Read** `.ntxp/ipdm/model-council.yaml` to get the project's model preferences
2. **Match tier** — Tier 1 uses local/cache (no model call), Tier 2 routes to Haiku via Model Council, Tier 3 routes to Sonnet/Opus via Model Council
3. **Check Model Reps** — if `ntxp-model-reps` plugin is active, delegate model-specific tasks to the appropriate rep (claude-rep, gemini-rep, etc.)
4. **Log** every routing decision to `.ntxp/highway/routing-log.jsonl`:

```jsonl
{"ts":"2026-10-26T12:00:00Z","intent":"estimate","matched":"ntxp-estimating","tier":3,"model":"opus","latency_ms":4200}
```

## Chaining Rules

When a task requires multiple skills in sequence, Highway builds a pipeline:

1. **Identify dependencies** — which skill outputs feed the next skill's inputs
2. **Parallelize independents** — run non-dependent skills concurrently
3. **Pass context via IPDM** — shared state flows through `.ntxp/ipdm/project.yaml`
4. **Register outputs in Coda** — every platform URL or ID created goes to `.ntxp/coda/registry.yaml`
5. **Aggregate results** — collect outputs and present unified response

### Example Chain: New Project Setup

```
ntxp-id (auth → .ntxp/ipdm/identity.yaml)
    |
    v
ntxp-ipdm (create project record → .ntxp/ipdm/project.yaml)
    |
    +---> ntxp-folder-system (Drive folders → platforms.google_drive)  [parallel]
    +---> auto-deploy-claude-flow (init repo)                          [parallel]
    |
    v
ntxp-project-coda (collect links → .ntxp/coda/registry.yaml + crosswalk.yaml)
    |
    v
ntxp-model-council (configure routing → .ntxp/ipdm/model-council.yaml)
```

## Cost Tiers

| Tier | Latency | Cost | When | Credential Needed |
|------|---------|------|------|-------------------|
| 1 — Local | <100ms | $0 | Lookups, file ops, cached results | No |
| 2 — Fast | <2s | Low | Standard skill execution, simple generation | Via ntxp-secrets-vault |
| 3 — Deep | 2-30s | Medium-High | Complex reasoning, multi-file analysis, estimates | Via ntxp-secrets-vault |

## Persistence

Highway routing decisions and performance metrics are logged to `.ntxp/highway/routing-log.jsonl` for continuous optimization. The routing config lives at `.ntxp/highway/config.yaml` (bootstrapped by auto-deploy, updated by this skill). Both files are committed to the repo.
