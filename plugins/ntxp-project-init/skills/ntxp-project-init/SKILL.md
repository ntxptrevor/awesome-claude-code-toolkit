---
name: ntxp-project-init
description: "Sequences the start of a new NTXP project after asking the user to confirm: environment preflight, NTXP ID identity, authority check against IPDM, project registration, the v1.2 Drive folder tree, the Project Coda crosswalk, and model and executor choices, by calling the Forge skills that own each step. Hooks offer it when a new project, bid or award is mentioned. Use when someone says new project, new bid, award, kick off or set up a project. Not for questions about an existing project."
version: 3.0.0
owner: NTXP
requires:
  skills: [ntxp-id, ntxp-env-initialization, ntxp-ipdm, ntxp-projects, ntxp-folder-structure, ntxp-project-coda, ntxp-model-council, ntxp-model-router]
  connectors: [jobtread, google-drive]
provides: [project-start-sequencer]
---

# NTXP Project Init

A sequencer. It owns the question, the order and the evidence. It does not own project data, the folder layout, the crosswalk, identity or model choice: each of those belongs to a Forge skill, and this skill calls it. It writes no project data of its own.

## Rule Zero: ask first

Hooks only **offer** this skill. Never run a step because a hook said so.

1. Check which model seat is serving this session first. If it is a DeepSeek or GLM seat, ask only for the JobTread job id and which steps to run, nothing else. If the user volunteers owner, agency, bid, pricing or personnel details, say they must go to a permitted seat, stop collecting, and hand the rest to one (via `ntxp-model-router`) or ask the user to switch the session.
2. On a permitted seat, ask with AskUserQuestion: the JobTread job (its id, or "not yet"), the project name, and which steps to run (default all). Do not ask for the client, owner, agency or bid status: the owning skills read those from JobTread and the registry.
3. If the user declines, run the `decline` command that the offer printed (it records the decline for this project directory outside the repository, and the hook stays quiet for 12 hours). If the skill was invoked without an offer, there is nothing to record.
4. Committing or pushing anything is a separate confirmation.

## Steps and who owns them

| # | Step | Owner (call it, do not copy it) | Done when |
|---|---|---|---|
| 0 | Environment preflight | `ntxp-env-initialization` task preflight (`scripts/preflight.py --repo <forge> --json`) | Dependencies carry a status with evidence |
| 1 | Identity and credentials | `ntxp-id` (`/id`, `/vault`, `vault-clerk`) | Identity is `authenticated`; every needed key is located without exposing it |
| 2 | Authority | `ntxp-ipdm` (read only) | The user's role may start or approve this project, or the gap is stated |
| 3 | Register the project | `ntxp-projects` (JobTread job id is the key) | Dry run reviewed; upsert pushed and read back if the user supplies that skill's key file, otherwise `unavailable` with the reason |
| 4 | Folder tree | `ntxp-folder-structure` v1.2 | Tree built from the template, `_PERMISSIONS.md` written, `12 - HUB / MBE` and `!Public Share` present |
| 5 | Crosswalk | `ntxp-project-coda` | Coda persisted under `0 - Knowledge Base/0.2 Structured Data` |
| 6 | Models and executors | `ntxp-model-council`, `ntxp-model-router`, `ntxp-highway` | Choices recorded; privacy rules respected |
| 7 | Claude Flow (optional) | `references/claude-flow.md` | Only for development workspaces |
| 8 | Verify and report | this skill | Evidence table printed |
| 9 | Share back | `ntxp-model-council` knowledge base | Workflow row posted once |

Run steps in order. Steps that do not depend on each other may run in parallel.

## Step details

### 0. Preflight

Run the environment skill's task preflight for this task and project. A skill being present is not proof its connector works: record each dependency as `located`, `installed`, `authenticated`, `live-read`, `live-write` or `unavailable`, with evidence and a time. Stop and report if a dependency this project needs is `unavailable`.

### 1. Identity and credentials

Use `ntxp-id`, and only on a permitted seat (see Data boundaries). Request a credential through its process (name the key, the task and the reason; the approved agent reads one cell). A missing key goes to the vault's Add Secret or Add Password card; the value is never requested in chat. Do not use `ntxp-secrets-vault` (superseded). Never put a credential in chat, a log, a commit, a memory entry, a council field or the repository. The one exception is a key file that an owning skill documents as its only transport; see step 3.

### 2. Authority

Read `ntxp-ipdm` (the Integrated Project Delivery Method) for the method and decision rights that apply to starting a project (for example the "bid opening / award posted" trigger and who awards or removes subcontractors). IPDM holds company method, not per-project data: read it, never write project data into it. A change to IPDM goes only through `ntxp-change-gate` by the Director. If the rights are unclear, ask the user.

### 3. Register the project

Use `ntxp-projects`. The JobTread job id is the project id. If no JobTread job exists yet, say so and ask; this skill does not create one. Follow that skill's pipeline (build, payload, `--dry-run` first, then push and read back). The data includes pricing: never commit it.

`ntxp-projects` authenticates its push only through a key file (`NTXP_PROJECTS_WRITE_KEY_FILE`). The Forge's own rule says credentials are never written to a file, so the two conflict, and this skill does not settle that. The user supplies and owns that key file: outside any repository, owner-only permissions, deleted right after the call. Never create it by passing a value through chat or a log. If no key file is supplied, do the dry run, mark the push `unavailable`, say why, and continue with the other steps.

### 4. Folder tree

Use `ntxp-folder-structure` v1.2. Build from its template, never from a copy of another project. Write `_PERMISSIONS.md`, and confirm `12 - HUB / MBE` and `!Public Share` exist. Claude cannot change Drive sharing; flag it to a human with Drive admin rights and do not say it is applied. Do not use `ntxp-folder-system` (superseded). Creating folders only: no moves, renames or deletes here.

### 5. Crosswalk

Use `ntxp-project-coda`. It fires whenever a project is named; run `coda.py new` for this project and follow its loop (environment, locate, harvest, crosswalk, confirm, persist). Names alone never confirm a link, and JEV confidence is capped. Its persistence, JobTread notes mirror and Lightfield step are its own.

### 6. Models and executors

Executor choice and spend caps: `ntxp-model-router`. Decisions: `ntxp-model-council` (convene for decisions, not chores; never write the council's Councils, Turns, Decisions or Gates tabs by hand; record "council not convened" if the engine is absent). Handoffs and provider calls: `ntxp-highway`. This skill defines no routing table.

### 7. Claude Flow (development workspaces only)

See `references/claude-flow.md`. Pin the CLI (`@claude-flow/cli@3.75.3`). Never run `init --force` where `.claude/settings.json` or `CLAUDE.md` already exist, and ask before any overwrite.

### 8. Verify and report

Print one table: each step, its owner, its status word from the vocabulary above, the evidence, and the time. List what a human must still do (Drive sharing, a missing key, an `unavailable` dependency). Never report a step as done without a call that returned it.

### 9. Share back

Once per successful start, add one row to the council's Workflows tab (the steps, the skills called, anything that failed and how). Check for an existing row first.

## Data boundaries

These come from the Forge's own rules and apply to every step.

- DeepSeek and GLM never receive owner, agency, bid, pricing, personnel or credential content from this skill. Route that work to a permitted seat. The Forge's `AGENTS.md` says never for credentials, while its `CLAUDE.md` (2026-11-11) allows it through `ntxp-id`. The two disagree, so this skill follows the stricter one until the owner reconciles them. If a step needs a credential and the session is on a DeepSeek or GLM seat, stop that step and ask the user to move it to a permitted seat.
- Registry data holds pricing: never commit it, never paste it into a council field.
- Never commit a secret. Secrets go through `ntxp-id` only.
- Merge policy for the Forge: squash-merge your own PR when `skill-validate` is green; run `forge.py marketplace` after any change under `skills/` or `plugins/`.

## Hook

`hooks/hooks.json` registers one `UserPromptSubmit` hook (`hooks/bin/ntxp-project-init-hook.cjs`). It matches new-project, new-bid and award wording (never a bare project id, and a software request such as "set up a new project in React" stays quiet, so routine work is not interrupted), prints an offer that tells the model to ask first and to ignore software topics, waits 30 minutes between offers, and stays quiet for 12 hours after a decline. It never runs anything. It is Claude Code only; other platforms invoke the skill by name.

## Errors

| Problem | Action |
|---|---|
| An owning skill is not installed | Report it as `unavailable`; do not recreate its work here |
| No JobTread job | Stop at step 3 and ask |
| No Drive connector | Say the tree was not created; do not fake it |
| MCP server dropped | Run `node .claude/helpers/mcp-watchdog.cjs status` if present, continue without it, say so |
| User declines mid-way | Stop; keep what was done; list what remains |

## Not owned here

Retired: `auto-deploy-claude-flow` and a local routing-table skill named `ntxp-highway` (it collided with the Forge's). A local `.ntxp/` data layer and an `identity.yaml` were never part of the Forge and are not used.
