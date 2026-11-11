---
name: "ntxp-project-init"
description: "Creates, audits and hands off an NTXP project end to end, after asking the user to confirm: Claude Flow orchestration, NTXP ID authentication, the IPDM project record, the numbered NTXP Drive folder tree (1-13 plus !Public Share), the Project Coda link registry and platform crosswalk, knowledge-base wiring, and Model Council and model-router setup. Hooks offer it when a new project, bid or award is mentioned or no project record exists. Use for new projects and bids, awards, platform access audits, project handoff packages, and cross-platform ID or link lookups."
version: "2.0.0"
owner: "claude-code"
requires: ["ntxp-id", "ntxp-secrets-vault", "ntxp-model-council", "ntxp-folder-system"]
provides: ["ntxp-project-init", "project-coda-registry"]
---

# NTXP Project Init

One skill for the whole project lifecycle at the setup layer. It absorbs the old auto-deploy skill and the Project Coda workflow, and it is the writer for IPDM, the Coda registry and the crosswalk.

## Rule Zero: Ask First

Hooks only **offer** this skill. Never run a mode on a hook's say-so.

1. Ask with AskUserQuestion: which mode, then for `create` the project name, client/owner, contract type (JOC | CSP | Hard Bid | CM-at-Risk | Design-Build), cooperative (TIPS | BuyBoard | Sourcewell | Choice Partners | None), status (Pursuit | Pre-Con | Active), and which steps to run (default all).
2. If the user declines, set `declined: true` in `.claude-flow/data/ntxp-init-state.json` and drop it for the session.
3. Commit and push is its own confirmation (Step 9). Never push unasked.

## Modes

| Mode | Use when | Runs |
|---|---|---|
| `create` | New project, bid or award; or a workspace with no record | Steps 0-10 |
| `audit` | Which platforms are connected or missing; access check | Coda audit (`references/coda.md`) |
| `handoff` | Onboarding a person or exporting the project map | Coda handoff package |
| `resolve` | Another skill needs a project URL or a cross-platform id | Coda lookup: read-only |

## Create workflow

Run the confirmed steps in order; independent steps may run in parallel. After each step write its result to `.ntxp/ipdm/project.yaml` (source of truth) and log it.

### Step 0 - Preflight

1. Search the council knowledge base for an existing workflow before building (`council_kb_search "project init"` or read tabs 20, 21, 22 of the council sheet when the engine is absent). Reuse and cite its ID.
2. Confirm identity (Step 2) and that the vault sheet is not publicly shared (vault rule 3).

### Step 1 - Claude Flow core

Architecture, config and optimization plan: `references/claude-flow.md`. Hierarchical-mesh swarm, 6-8 active agents, hybrid memory with HNSW, 3-tier routing.

`--force` overwrites `.claude/settings.json`, `CLAUDE.md` and hooks. Never use it where they already exist.

```bash
if [ -f .claude/settings.json ] || [ -f CLAUDE.md ]; then
  echo "already initialized: skip init, verify only"   # ask first before any --force; back up first:
  # cp -r .claude ".claude.bak-$(date +%s)" && cp CLAUDE.md "CLAUDE.md.bak-$(date +%s)"
else
  npx @claude-flow/cli@3.75.3 init
fi
test -f CLAUDE.md && test -f .mcp.json && test -d .claude && test -d .claude-flow && echo "claude-flow OK"
```

Pin the CLI version (`@claude-flow/cli@3.75.3`); do not use `@latest`, and do not widen `npx` allow rules.

### Step 2 - NTXP ID

NTXP ID is the identity and credential layer for every later step.

1. Read `.ntxp/ipdm/identity.yaml`. If missing or expired, run the `ntxp-id` plugin (`/id`). This skill only **reads** identity; the plugin writes it. If the plugin is unavailable, log it, continue, and mark identity `unverified` in the report.
2. Credentials resolve only through `anthropic-skills:ntxp-secrets-vault`: look up with `find_vault_entry` (masked, last 4 only). Treat `NO KEY`, `EXPIRED` or a placeholder as missing.
3. A missing key is never requested in chat. Send the Add Secret card link, or the NTXP ID share-sheet shortcut (clipboard-only capture), wait for "filed", confirm with `find_vault_entry`, then continue.
4. No key, token, password or secret value may appear in any file this skill writes, nor in a reply, commit, log or council field. Step 8 enforces it.
5. Register the environment with the council (`council_env`, tab 31 Environments) when the engine is present.

### Step 3 - IPDM record

Create `.ntxp/ipdm/project.yaml` from the answers: id `NTXP-{YYYY}-{SEQ}` (next free sequence), name, owner, contract type, cooperative, status, and the six platform keys. Template: `references/templates.md`.

### Step 4 - Folder structure

Full numbered tree, CSI subfolders `4.3.1`-`4.3.33`, permissions and output map: `references/folder-structure.md`. Numbers are permanent and never reused.

1. Awarded projects go under `NTXP > !Active Projects`; bids under `NTXP PM > !Active Bids`. Root name: `[Client] [Project Name]`.
2. Create the tree through the Google Drive connector when present (parents first). Otherwise write `.ntxp/ipdm/folder-manifest.yaml` listing every folder and number, and say it was not created.
3. Write `_PERMISSIONS.md`: `!Public Share` public read-only, everything else NTXP-only read/write. Claude cannot change Drive sharing; flag it to a human with Drive admin rights and do not claim it is applied.
4. Confirm folder 13 (HUB/MBE) and `!Public Share` exist before calling the tree live.
5. Write the Drive folder URL to `platforms.google_drive`.

Init only creates folders. It never moves, renames or deletes files (no triage here).

### Step 5 - Project Coda

Build the registry and crosswalk, validate links, produce the access card. Everything is in `references/coda.md`: registry schema, crosswalk, sync log, validation, summary card. If the Forge `ntxp-project-coda` skill is installed, delegate project biography, confidence grading and the Lightfield note/plan step to it; this step still owns the local registry.

### Step 6 - Knowledge-base wiring

Search-then-save for every NTXP skill: search `.ntxp/ipdm/project.yaml` and `.ntxp/coda/registry.yaml` before external calls, save outputs back to IPDM, register new links and ids in Coda and the crosswalk. Bindings live in `.ntxp/ipdm/skill-config.yaml` (template in `references/templates.md`).

### Step 7 - Model Council and routing

Read or create `.ntxp/ipdm/model-council.yaml` through `anthropic-skills:ntxp-model-council`. Executor choice, spend caps and task-aware model selection belong to the Forge `ntxp-model-router`; agent handoffs and provider calls belong to the Forge `ntxp-highway`. This skill does not define a routing table or duplicate either one. Record in the report which of them are installed.

### Step 8 - Verify

- Every file from Steps 1-7 exists and parses.
- Platform keys are exactly `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot`.
- No secrets: `grep -rniE "(api[_-]?key|token|secret|password)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,}" .ntxp/` returns nothing.
- The folder tree has 1-13 and `!Public Share`.
- Identity state is recorded (`verified` or `unverified`).

### Step 9 - Commit (separate confirmation)

Ask "Commit and push the setup?". Only on yes:

```bash
git add .claude-flow/ .claude/ .mcp.json CLAUDE.md .ntxp/
git commit -m "Initialize NTXP project <id>"
git push -u origin "$(git rev-parse --abbrev-ref HEAD)"
```

Retry a failed push up to 4 times (2s, 4s, 8s, 16s).

### Step 10 - Share back and report

Share what was learned with the council (see Council wiring), then print the project card: id, name, platform links and status, folder location, identity state, routing, skipped steps, and what a human must still do (Drive permissions, any `unreachable` link).

## Council wiring

The Model Council is the team's shared channel and knowledge base.

- **Look first**: Step 0. Cite workflow IDs you reuse.
- **Convene for decisions, not chores.** Use `council_run` when a user wants to deviate from the numbering or add a root folder, change the platform keys or the IPDM file layout, or pick a method that would change how NTXP works (`change_type: methodology`, which always gates for approval). Routine setup uses `council_route`, not a council.
- **Confidentiality**: project owner, client, agency, bid, pricing and personnel content must never reach the Ledger (DeepSeek) or Mason (GLM) seats. Pass `confidential: true` for any subject that carries them.
- **Hard rules** are enforced in code: at least 3 distinct providers, one short paragraph per turn, spend ceilings. Never put a secret in any council field.
- **Gates**: show the gate text, wait for the user's direction, never pick an option on a methodology, classification, privacy or payment gate.
- **No engine here** (cloud session, claude.ai, phone): read tabs 20-22 through the Google Sheets connector, append findings with the same columns, and record "council not convened" with the reason. Never write a row into 10 Councils, 11 Turns, 12 Decisions or 13 Gates by hand, and never claim a consensus that was not run.
- **Share back** after a successful init: one row on 21 Workflows (this workflow, steps, tools), and a row on 23 Skills Crosswalk when the skill's packaging or version changed. Duplicates are checked before appending.

## IPDM wiring

IPDM is the source of truth; this skill is its writer. File ownership:

| File | Writer | Readers |
|---|---|---|
| `.ntxp/ipdm/project.yaml` | this skill | all skills |
| `.ntxp/ipdm/identity.yaml` | `ntxp-id` plugin | all skills |
| `.ntxp/ipdm/skill-config.yaml` | this skill | all skills |
| `.ntxp/ipdm/model-council.yaml` | `ntxp-model-council` | `ntxp-model-router`, this skill |
| `.ntxp/coda/registry.yaml`, `crosswalk.yaml`, `sync-log.jsonl` | this skill | all skills |

## Forge wiring

This package is a plugin (`plugins/ntxp-project-init/`) so its hooks run: a skill's own `hooks/` folder does not execute when delivered through the Claude account channel, a plugin's `hooks/hooks.json` does. It ships no `bin/` (claude.ai rejects it); the hook script is in `scripts/`. Frontmatter carries the keys the Forge skill mesh requires: `version`, `owner`, `requires`, `provides`.

To back it up to `NTXP-TX/ntxp-forge` (from a machine whose `gh` is signed in; never export the vault token): clone, branch `feat/ntxp-project-init` from latest `main`, copy `plugins/ntxp-project-init/`, then run:

```bash
python3 skills/ntxp-skill-forge/forge/forge.py verify --repo . --write-source
python3 skills/ntxp-skill-forge/forge/forge.py marketplace --repo .
python3 .github/ntxp/skill_mesh.py skills plugins --deps-warn
```

Open the PR, wait for `skill-validate`, squash-merge. Do not remove or change the existing Forge `ntxp-project-coda` (v1.0.0): this plugin delegates to it and does not replace it. Only the old local `auto-deploy-claude-flow` and local Coda stub were retired, and neither is in the Forge. Forge never rewrites skill wording; hooks and scripts are Claude Code only, other platforms use the manual trigger.

## Error handling

| Problem | Action |
|---|---|
| Plugin or skill not enabled | Log, continue, mark the step partial |
| MCP server dropped | `node .claude/helpers/mcp-watchdog.cjs status`; proceed without it and say so |
| No Drive connector | Write `folder-manifest.yaml`, flag not created |
| Init partly failed | Re-run once on a fresh workspace; report exactly what is missing; never fake success |
| Vault sheet publicly shared | Stop; run the vault's `remove_public_link_sharing` first |
| User declines mid-way | Stop; keep completed steps; list what remains |

## Superseded

Replaces `auto-deploy-claude-flow` and the local `ntxp-project-coda` stub. `ntxp-ipdm` remains the data layer. Routing belongs to the Forge `ntxp-model-router` and handoffs to the Forge `ntxp-highway`; the local routing-table skill that shared the `ntxp-highway` name was retired to avoid a collision.

## NTXP Interop

- **Knowledge Base**: search `.ntxp/ipdm/project.yaml` and `.ntxp/coda/registry.yaml` before external calls; save outputs back to `.ntxp/ipdm/project.yaml`.
- **Credentials**: `ntxp-id` then `anthropic-skills:ntxp-secrets-vault`; never hardcode.
- **Model Routing**: read `.ntxp/ipdm/model-council.yaml`; call `ntxp-model-council` if missing.
- **Skill Bindings**: `.ntxp/ipdm/skill-config.yaml`.
- **Platform Keys**: `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot`; no aliases.
