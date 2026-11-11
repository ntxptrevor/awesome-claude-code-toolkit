---
name: "NTXP Project Init"
description: "Creates and initializes a new NTXP project end to end, after asking the user to confirm: Claude Flow orchestration, the numbered NTXP Drive folder structure (1-13 plus !Public Share), the IPDM project record, Project Coda link registry and platform crosswalk, knowledge-base wiring, and Model Council/Highway routing. Hooks offer this skill automatically when a new project, bid or award is mentioned or when no project record exists. Use for new projects, new bids, awards, onboarding a repo, or resetting a project's setup."
---

# NTXP Project Init

One skill that replaces the old auto-deploy skill and ties together Claude Flow, the NTXP folder system, IPDM, Project Coda, the knowledge base and model routing.

## Rule Zero: Ask First

Never run this workflow on a hook's say-so. The hooks only **offer** it. Before any step:

1. Ask the user (AskUserQuestion) whether they want to create a new project now, and collect: project name, client/owner, contract type (JOC | CSP | Hard Bid | CM-at-Risk | Design-Build), cooperative (TIPS | BuyBoard | Sourcewell | Choice Partners | None), status (Pursuit | Pre-Con | Active), and which steps to run (default: all).
2. If the user declines, record the decline in `.claude-flow/data/ntxp-init-state.json` (`declined: true`) and drop it. Do not ask again this session.
3. Committing and pushing is a separate confirmation (Step 9). Never push without it.

## When This Fires

| Trigger | Source |
|---|---|
| "new project", "new bid", "kick off", "awarded", "set up a project", "project init", an `NTXP-YYYY-SEQ` id | UserPromptSubmit hook (`ntxp-project-init-hook.cjs prompt`) |
| Session opens in a workspace with no project record (`.ntxp/ipdm/project.yaml` missing or empty id) | SessionStart hook (`ntxp-project-init-hook.cjs session`) |
| User invokes the skill directly | Manual |

## Workflow

Run the confirmed steps in order. Steps within a phase that don't depend on each other run in parallel. After each step, write its result into `.ntxp/ipdm/project.yaml` (the source of truth) and log it.

### Step 1 — Claude Flow core

Purpose, architecture, config and optimization plan are in `references/claude-flow.md`. In short: hierarchical-mesh swarm, 6-8 agents for coding work, hybrid memory with HNSW, 3-tier model routing, hooks for learning and checkpoints.

```bash
npx claude-flow@alpha init --force
test -f CLAUDE.md && test -f .mcp.json && test -d .claude/agents && test -d .claude/skills \
  && test -f .claude/settings.json && test -d .claude-flow && echo "claude-flow OK"
```

If a check fails, re-run init once, then report what is missing. Version pinning: prefer a pinned `@claude-flow/cli@<version>` in `.mcp.json` over `@latest`, and do not widen the `npx` allow rules in `settings.json`.

### Step 2 — Auth

Authenticate through the `ntxp-id` plugin (`/id`). It writes `.ntxp/ipdm/identity.yaml`. If the plugin is not enabled, log it and continue; later steps that need credentials resolve them through `anthropic-skills:ntxp-secrets-vault`. Never write a key, token or password into any file.

### Step 3 — IPDM project record

Create `.ntxp/ipdm/project.yaml` from the answers in Rule Zero, with id `NTXP-{YYYY}-{SEQ}` (next free sequence) and the six platform keys. Template: `references/templates.md`.

### Step 4 — Folder structure

The full numbered tree (1-13 plus `!Public Share`, with CSI subfolders 4.3.1-4.3.33) is in `references/folder-structure.md`. It is permanent: numbers are never reused or renumbered.

1. Where it goes: awarded projects under `NTXP > !Active Projects`; bids under `NTXP PM > !Active Bids`. Name the root `[Client] [Project Name]`.
2. Create the tree with the Google Drive connector when available (folder mime type, parents first). If no Drive tool is available, write `.ntxp/ipdm/folder-manifest.yaml` listing every folder and number so it can be created later, and say so.
3. Write `_PERMISSIONS.md` at the project root: `!Public Share` is public read-only; everything else is NTXP employee-only read/write. Claude cannot change Drive sharing, so flag this to a human with Drive admin rights. Do not claim it is applied.
4. Confirm 13 (HUB/MBE) and `!Public Share` exist before calling the folder "live".
5. Write the Drive folder URL to `platforms.google_drive` in IPDM.

Hard rules inherited from the folder system: no deletion ever (obsolete files get ` - VOID`), nothing leaves its project tree, low-confidence moves go to Trevor.

### Step 5 — Project Coda

Create `.ntxp/coda/registry.yaml`, `.ntxp/coda/crosswalk.yaml` and `.ntxp/coda/sync-log.jsonl` (templates in `references/templates.md`). Copy platform URLs from IPDM into the registry, keep all major links (Drive, eBuilder, JobTread, BuildingConnected, Procore, HubSpot, owner/architect portals, NTXP tools), and fill the crosswalk so one real-world entity maps to its id on every platform. IPDM is the write source; Coda is the read-optimized index. Validate links through the matching connector and mark each `connected | pending | unreachable | not-applicable`.

### Step 6 — Knowledge base wiring

Every NTXP skill follows search-then-save:

1. Search `.ntxp/ipdm/project.yaml` and `.ntxp/coda/registry.yaml` before any external call.
2. Save outputs back to IPDM; register new links and ids in Coda and the crosswalk.
3. Declared read/write bindings live in `.ntxp/ipdm/skill-config.yaml` (template in `references/templates.md`).
4. Credentials: `ntxp-id` then `ntxp-secrets-vault`. Never hardcode.

### Step 7 — Model routing

Read or create `.ntxp/ipdm/model-council.yaml` through `anthropic-skills:ntxp-model-council`. Create `.ntxp/highway/config.yaml` with the routing table from the `ntxp-highway` skill (10 routes) and an empty `routing-log.jsonl`. Tier 1 local lookups, Tier 2 Haiku, Tier 3 Sonnet/Opus.

### Step 8 — Verify

- All files from Steps 1-7 exist and parse.
- Platform keys are exactly: `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot`.
- No secrets in any `.ntxp/` file (`grep -riE "(api[_-]?key|token|secret|password)\s*[:=]"`).
- Folder tree has 1-13 and `!Public Share`.

### Step 9 — Commit (separate confirmation)

Ask: "Commit and push the setup?" Only on yes:

```bash
git add .claude-flow/ .claude/ .mcp.json CLAUDE.md .ntxp/
git commit -m "Initialize NTXP project <id>"
git push -u origin "$(git rev-parse --abbrev-ref HEAD)"
```

Retry a failed push up to 4 times with backoff (2s, 4s, 8s, 16s).

### Step 10 — Report

Print the project card: id, name, platform links with status, folder tree location, auth state, model routing, what was skipped, and what a human still must do (Drive permissions, any `unreachable` link).

## Error Handling

| Problem | Action |
|---|---|
| Plugin or skill not enabled | Log, continue; mark the step partial |
| MCP server dropped | Run `node .claude/helpers/mcp-watchdog.cjs status`; proceed without it and say so |
| No Drive connector | Write `folder-manifest.yaml`, flag as not created |
| Init partly failed | Re-run once; report exactly what is missing; do not fake success |
| User declines mid-way | Stop; leave completed steps in place; list what remains |

## Superseded Skills

This skill replaces `auto-deploy-claude-flow`. `ntxp-ipdm`, `ntxp-project-coda` and `ntxp-highway` remain as the data and routing layers it writes to; their details are summarized here so this skill is self-contained.

## NTXP Interop

- **Knowledge Base**: Search `.ntxp/ipdm/project.yaml` and `.ntxp/coda/registry.yaml` before external calls. Save outputs back to `.ntxp/ipdm/project.yaml`.
- **Credentials**: Auth via `ntxp-id` plugin, secrets via `anthropic-skills:ntxp-secrets-vault`, never hardcode.
- **Model Routing**: Read `.ntxp/ipdm/model-council.yaml`. Call `ntxp-model-council` if missing.
- **Skill Bindings**: Check `.ntxp/ipdm/skill-config.yaml`.
- **Platform Keys**: `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot`, no aliases.
