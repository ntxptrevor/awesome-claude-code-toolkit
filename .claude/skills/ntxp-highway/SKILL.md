---
name: "NTXP Highway"
description: "High-speed skill routing and orchestration layer for NTXP. Routes tasks to the optimal skill, model, or agent based on intent classification, cost tier, and latency budget. Works alongside Model Council and Model Reps to form the NTXP intelligence stack. Use when a task could be handled by multiple skills and needs fast, automatic routing — or when building multi-skill workflows that chain outputs across the NTXP ecosystem."
---

# NTXP Highway

## What This Skill Does

Highway is the fast-lane router for NTXP's skill ecosystem. When a task arrives, Highway classifies intent, checks the skill registry, evaluates cost/latency tiers, and dispatches to the best handler — all before the user waits for a response. It replaces manual skill invocation with automatic, intelligent routing.

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
```

## Routing Table

| Intent Pattern | Primary Skill | Fallback | Tier |
|---------------|---------------|----------|------|
| estimate, price, cost | ntxp-estimating | rsmeans-estimate-generator | 3 |
| takeoff, quantity, measure | ntxp-quantity-takeoff | demolition-takeoff | 3 |
| bid, ITB, solicit | ntxp-project-itb-brief | itb-generator | 2 |
| folder, file, organize | ntxp-folder-system | ntxp-folder-structure | 1 |
| schedule, SOV, pay app | dallas-isd-sov-payapp-review | estimating | 3 |
| submittal, RFI | ntxp-submittal-command | specs-skill | 2 |
| credential, key, secret | ntxp-secrets-vault | — | 1 |
| markup, redline, plan | ntxp-pdf-markups-and-redlines | apply-construction-markups | 2 |
| project setup, init | auto-deploy-claude-flow | init | 1 |
| model, AI, council | ntxp-model-council | — | 2 |

## Chaining Rules

When a task requires multiple skills in sequence, Highway builds a pipeline:

1. **Identify dependencies** — which skill outputs feed the next skill's inputs
2. **Parallelize independents** — run non-dependent skills concurrently
3. **Pass context via IPDM** — shared state flows through `.ntxp/ipdm/project.yaml`
4. **Aggregate results** — collect outputs and present unified response

### Example Chain: New Project Setup

```
ntxp-id (auth)
    |
    v
ntxp-ipdm (create project record)
    |
    +---> ntxp-folder-system (create Drive folders)  [parallel]
    +---> auto-deploy-claude-flow (init repo)         [parallel]
    |
    v
ntxp-project-coda (collect all platform links)
    |
    v
ntxp-model-council (configure model routing for project)
```

## Cost Tiers

| Tier | Latency | Cost | When |
|------|---------|------|------|
| 1 — Local | <100ms | $0 | Lookups, file ops, cached results |
| 2 — Fast | <2s | Low | Standard skill execution, simple generation |
| 3 — Deep | 2-30s | Medium-High | Complex reasoning, multi-file analysis, estimates |

## Persistence

Highway routing decisions and performance metrics are logged to `.ntxp/highway/routing-log.jsonl` for continuous optimization. The routing table itself lives in this skill and is updated via skill edits.
