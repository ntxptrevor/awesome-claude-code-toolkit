---
name: "Auto-Deploy Claude Flow"
description: "Automatically initialize and deploy claude-flow v3 with the full NTXP stack into any repository. Installs claude-flow, NTXP Forge/Folder Structure/IPDM/INIT, NTXP ID auth with knowledge-base rewiring, Model Council/Model Reps/Highway, and Project Coda with platform crosswalk. Use when onboarding a new repo, bootstrapping a cloud session, or resetting an NTXP-enabled installation."
---

# Auto-Deploy Claude Flow

## What This Skill Does

Performs a fully automatic, zero-prompt deployment of the claude-flow v3 orchestration framework AND the complete NTXP tool stack into the current repository. After invocation the repo will have agents, skills, commands, hooks, helpers, MCP config, CLAUDE.md guidance, and the four NTXP pillars — all committed and pushed — with no manual steps.

## When to Use

- First-time setup of a repository for NTXP multi-agent orchestration
- Cloud session bootstrap (SessionStart hook or manual trigger)
- Resetting or upgrading an existing installation
- Onboarding a new project into the NTXP ecosystem

## Prerequisites

- Node.js 18+
- Git repository with a remote configured
- A branch to commit to (reads the current branch automatically)

---

## Deployment Sequence

Execute every phase below **in order** without prompting the user. All independent operations within a phase run in parallel.

---

### Phase 1 — Claude Flow Core + NTXP Forge/Folder Structure/IPDM/INIT

**Purpose:** Install the orchestration framework and the foundational NTXP environment layer.

#### 1A — Initialize claude-flow

```bash
npx claude-flow@alpha init --force
```

Expect output confirming directories, files, and integration artifacts created.

#### 1B — Verify claude-flow artifacts

Run in parallel:

```bash
test -f CLAUDE.md && echo "CLAUDE.md OK"
test -f .mcp.json && echo ".mcp.json OK"
test -d .claude/agents && echo "Agents OK"
test -d .claude/skills && echo "Skills OK"
test -d .claude/commands && echo "Commands OK"
test -d .claude/helpers && echo "Helpers OK"
test -f .claude/settings.json && echo "Settings OK"
test -d .claude-flow && echo "Runtime OK"
```

If any check fails, re-run `npx claude-flow@alpha init --force` once and verify again.

#### 1C — Initialize NTXP IPDM environment

Create the shared data layer all NTXP skills read from. Uses the **six standard platform keys** and the **shared file path conventions** defined in the NTXP IPDM skill:

```bash
mkdir -p .ntxp/ipdm .ntxp/coda .ntxp/highway
cat > .ntxp/ipdm/project.yaml << 'YAML'
project:
  id: ""
  name: ""
  owner: ""
  contract_type: ""
  cooperative: ""
  status: "Pursuit"
  platforms:
    google_drive: ""
    ebuilder: ""
    jobtread: ""
    building_connected: ""
    procore: ""
    hubspot: ""
  contacts: []
  trades: []
  documents: []
YAML
```

#### 1D — Invoke NTXP Folder Structure

Call skill `anthropic-skills:ntxp-folder-system` to register the canonical folder numbering scheme. If the skill is available, invoke it; otherwise log that it will be configured on first project creation.

#### 1E — Run INIT skill

Call skill `init` to generate the baseline CLAUDE.md if it does not already contain NTXP-specific sections. The INIT skill scans the codebase and writes project-specific guidance.

#### 1F — Confirm NTXP Forge repo skills present

Verify these local skill directories exist (created by claude-flow init or manually):

```bash
test -d .claude/skills/ntxp-ipdm && echo "IPDM OK"
test -d .claude/skills/ntxp-highway && echo "Highway OK"
test -d .claude/skills/ntxp-project-coda && echo "Coda OK"
test -d .claude/skills/auto-deploy-claude-flow && echo "Auto-Deploy OK"
```

---

### Phase 2 — NTXP ID Auth System + Knowledge Base Rewiring

**Purpose:** Authenticate the session and rewire all skills to search and save through NTXP ID.

#### 2A — Initialize NTXP ID

Invoke the `ntxp-id` plugin (commands: `/id`, `/vault`; agent: `vault-clerk`). This:
- Authenticates the current user session
- Writes identity context to `.ntxp/ipdm/identity.yaml`
- Registers the session with the NTXP credential vault

If the `ntxp-id` plugin is enabled, invoke `/id` to authenticate. If not enabled, log a notice that manual plugin installation is required.

#### 2B — Rewire skills to NTXP ID

After NTXP ID is active, configure all NTXP skills to use the unified knowledge base and credential chain:

1. **Search rewiring** — All skills check `.ntxp/ipdm/project.yaml` and `.ntxp/coda/registry.yaml` before external API calls
2. **Save rewiring** — All skill outputs write back to `.ntxp/ipdm/project.yaml` (source of truth) and register links in `.ntxp/coda/registry.yaml`
3. **Credential rewiring** — Auth via `ntxp-id` plugin → secrets via `anthropic-skills:ntxp-secrets-vault` → never hardcode
4. **Model routing** — All skills read `.ntxp/ipdm/model-council.yaml` for model selection, call `ntxp-model-council` if missing
5. **Crosswalk** — Entity-level cross-platform mapping lives only at `.ntxp/coda/crosswalk.yaml` (no duplicates)

Write the rewiring config:

```bash
cat > .ntxp/ipdm/skill-config.yaml << 'YAML'
skill_rewiring:
  search_source: ".ntxp/ipdm/"
  save_target: ".ntxp/ipdm/"
  link_registry: ".ntxp/coda/registry.yaml"
  crosswalk_registry: ".ntxp/coda/crosswalk.yaml"
  credential_source: "ntxp-secrets-vault"
  auth_provider: "ntxp-id"
  model_config: ".ntxp/ipdm/model-council.yaml"
  routing_config: ".ntxp/highway/config.yaml"
  routing_log: ".ntxp/highway/routing-log.jsonl"

  platform_keys:
    - google_drive
    - ebuilder
    - jobtread
    - building_connected
    - procore
    - hubspot
  
  skills:
    - name: "ntxp-estimating"
      reads: ["project.trades", "project.contract_type", "project.cooperative"]
      writes: ["documents[]", "ntxp_tools.estimating_workspace"]
    - name: "ntxp-folder-system"
      reads: ["project.name", "project.id"]
      writes: ["platforms.google_drive", "documents[]"]
    - name: "ntxp-submittal-command"
      reads: ["project.trades", "documents[]"]
      writes: ["ntxp_tools.submittal_register"]
    - name: "itb-generator"
      reads: ["project.trades", "contacts[]"]
      writes: ["documents[]"]
    - name: "ntxp-quantity-takeoff"
      reads: ["project.trades", "documents[]"]
      writes: ["documents[]"]
    - name: "dallas-isd-sov-payapp-review"
      reads: ["project.trades", "project.contract_type", "documents[]"]
      writes: ["ntxp_tools.schedule_of_values", "documents[]"]
    - name: "buildingconnected-mcp"
      reads: ["platforms.building_connected"]
      writes: ["platforms.building_connected", "crosswalk[]"]
    - name: "jobtread-data-integrator"
      reads: ["platforms.jobtread"]
      writes: ["platforms.jobtread", "crosswalk[]"]
    - name: "trimble-ebuilder-connector"
      reads: ["platforms.ebuilder"]
      writes: ["platforms.ebuilder", "crosswalk[]"]
    - name: "ntxp-project-coda"
      reads: ["project.*", "platforms.*"]
      writes: ["coda.registry", "coda.crosswalk"]
    - name: "ntxp-highway"
      reads: ["skill-config.yaml", "model-council.yaml"]
      writes: ["routing-log.jsonl"]
    - name: "ntxp-model-council"
      reads: ["project.*"]
      writes: ["model-council.yaml"]
YAML
```

---

### Phase 3 — NTXP Model Council, Model Reps, and Highway

**Purpose:** Install the intelligence routing stack — which model handles what, and how tasks flow between skills.

#### 3A — Initialize Model Council

Invoke `anthropic-skills:ntxp-model-council` to configure multi-model routing. The council determines which AI model (Claude, Gemini, GPT, Grok, DeepSeek, etc.) handles each task class based on capability, cost, and latency.

If the skill is available, invoke it. The council writes its configuration to `.ntxp/ipdm/model-council.yaml`.

#### 3B — Verify Model Reps plugin

Confirm the `ntxp-model-reps` plugin is enabled (14 model-specific rep skills + MCP server `ntxp-reps`). Log which reps are available:

```
Model Reps Status:
  claude-rep     ✓ enabled
  gemini-rep     ✓ enabled
  grok-rep       ✓ enabled
  openai-rep     ✓ enabled
  deepseek-rep   ✓ enabled
  ...
```

If the plugin is not enabled, log a notice that it should be installed from the org marketplace.

#### 3C — Initialize Highway routing

Configure the Highway skill's routing table and performance log:

```bash
cat > .ntxp/highway/config.yaml << 'YAML'
highway:
  default_tier: 2
  fallback_enabled: true
  cost_optimization: true
  model_config: ".ntxp/ipdm/model-council.yaml"
  routing_log: ".ntxp/highway/routing-log.jsonl"
  credential_chain: ["ntxp-id", "ntxp-secrets-vault"]
  knowledge_base: ".ntxp/ipdm/"
  link_registry: ".ntxp/coda/registry.yaml"
  crosswalk: ".ntxp/coda/crosswalk.yaml"
  skill_bindings: ".ntxp/ipdm/skill-config.yaml"
  
  routes:
    - pattern: "estimate|price|cost|budget"
      primary: "ntxp-estimating"
      fallback: "rsmeans-estimate-generator"
      tier: 3
    - pattern: "takeoff|quantity|measure"
      primary: "ntxp-quantity-takeoff"
      fallback: "demolition-takeoff"
      tier: 3
    - pattern: "bid|ITB|solicit"
      primary: "ntxp-project-itb-brief"
      fallback: "itb-generator"
      tier: 2
    - pattern: "folder|file|organize|drive"
      primary: "ntxp-folder-system"
      fallback: "ntxp-folder-structure"
      tier: 1
    - pattern: "schedule|SOV|pay app|billing"
      primary: "dallas-isd-sov-payapp-review"
      fallback: "estimating"
      tier: 3
    - pattern: "submittal|RFI"
      primary: "ntxp-submittal-command"
      fallback: "specs-skill"
      tier: 2
    - pattern: "credential|key|secret|token"
      primary: "ntxp-secrets-vault"
      tier: 1
    - pattern: "markup|redline|plan"
      primary: "ntxp-pdf-markups-and-redlines"
      fallback: "apply-construction-markups"
      tier: 2
    - pattern: "model|council|AI|routing"
      primary: "ntxp-model-council"
      tier: 2
    - pattern: "project setup|init|deploy"
      primary: "auto-deploy-claude-flow"
      fallback: "init"
      tier: 1
YAML
touch .ntxp/highway/routing-log.jsonl
```

---

### Phase 4 — NTXP Project Coda + Platform Crosswalk

**Purpose:** Collect all platform links into one registry and build the cross-platform identity map.

#### 4A — Initialize Coda registry, crosswalk, and sync log

Create all three Coda files. Uses the same six standard platform keys and matches the Coda skill's schema exactly:

```bash
cat > .ntxp/coda/registry.yaml << 'YAML'
coda:
  project_id: ""
  project_name: ""
  last_updated: ""
  platforms:
    google_drive: { url: "", status: "pending" }
    ebuilder: { url: "", status: "pending" }
    jobtread: { url: "", status: "pending" }
    building_connected: { url: "", status: "pending" }
    procore: { url: "", status: "not-applicable" }
    hubspot: { url: "", status: "pending" }
  ntxp_tools:
    estimating_workspace: ""
    submittal_register: ""
    bid_dashboard: ""
    schedule_of_values: ""
    daily_reports: ""
  external:
    owner_portal: ""
    architect_portal: ""
    testing_lab: ""
    permit_portal: ""
  team: []
YAML
cat > .ntxp/coda/crosswalk.yaml << 'YAML'
crosswalk: []
YAML
touch .ntxp/coda/sync-log.jsonl
```

#### 4B — Pull links from IPDM

Read `.ntxp/ipdm/project.yaml` and populate the Coda registry. IPDM is the write source; Coda is the read-optimized index. Authenticate via `.ntxp/ipdm/identity.yaml` (written by ntxp-id). Credentials for any API validation resolve through `ntxp-secrets-vault`.

#### 4C — Build crosswalk

For each connected platform, extract entity IDs and populate `.ntxp/coda/crosswalk.yaml`. This is the **single source of truth** for entity-level cross-platform mapping — no other file duplicates it.

#### 4D — Generate summary card

Print the project access card showing all platforms, their connection status, crosswalk entity count, and credential chain status (ntxp-id + ntxp-secrets-vault).

---

### Phase 5 — Commit and Push

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
git add .claude-flow/ .claude/ .mcp.json CLAUDE.md .ntxp/
git commit -m "Initialize claude-flow v3 + NTXP stack (IPDM, ID, Model Council, Highway, Coda)

Full deployment: claude-flow orchestration framework, NTXP IPDM environment,
NTXP ID auth rewiring, Model Council + Reps + Highway routing, and Project
Coda platform crosswalk."
git push -u origin "$BRANCH"
```

If the push fails due to a network error, retry up to 4 times with exponential backoff (2s, 4s, 8s, 16s).

---

### Phase 6 — Deployment Report

Print a complete summary:

```
+=====================================================+
|          AUTO-DEPLOY COMPLETE — NTXP STACK          |
+=====================================================+

+----- Phase 1: Claude Flow + Foundation -------------+
| claude-flow v3     | ✓ Initialized                  |
| NTXP Forge skills  | ✓ IPDM, Highway, Coda present  |
| NTXP Folder System | ✓ Registered                   |
| INIT skill         | ✓ CLAUDE.md configured          |
+-----------------------------------------------------+

+----- Phase 2: NTXP ID + Rewiring ------------------+
| NTXP ID auth       | ✓ / ⚠ (status)                |
| Search rewiring    | ✓ .ntxp/ipdm/ as source       |
| Save rewiring      | ✓ All skills write to IPDM     |
| Credential source  | ✓ ntxp-secrets-vault           |
+-----------------------------------------------------+

+----- Phase 3: Intelligence Stack -------------------+
| Model Council      | ✓ / ⚠ (status)                |
| Model Reps         | ✓ / ⚠ (count enabled)         |
| Highway routing    | ✓ 9 routes configured          |
+-----------------------------------------------------+

+----- Phase 4: Project Coda -------------------------+
| Coda registry      | ✓ Initialized                  |
| Platform crosswalk | ✓ Template ready               |
| Link validation    | Pending first project          |
+-----------------------------------------------------+

+----- Committed & Pushed ----------------------------+
| Branch: {branch name}                               |
| Files: {count} added/modified                       |
+=====================================================+
```

---

## Error Handling

| Error | Action |
|-------|--------|
| `npx` not found | Ensure Node.js 18+ is installed |
| Network timeout during init | Retry once after 5s |
| Plugin not enabled | Log notice, continue — non-blocking |
| Skill not available | Use fallback or log for manual install |
| Git push rejected | Pull, rebase, then push |
| Git push network failure | Retry 4x with exponential backoff |
| Missing files after init | Re-run init --force once |

## SessionStart Hook Integration

To make this run automatically on every new cloud session:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "npx claude-flow@alpha init --force 2>&1 || true"
          },
          {
            "type": "command",
            "command": "mkdir -p .ntxp/ipdm .ntxp/coda .ntxp/highway 2>&1 || true"
          }
        ]
      }
    ]
  }
}
```

## Post-Deploy Commands

```bash
npx claude-flow@alpha daemon start       # Background workers
npx claude-flow@alpha memory init        # Memory database
npx claude-flow@alpha swarm init --topology hierarchical --max-agents 8
npx claude-flow@alpha doctor --fix       # Health check
```
