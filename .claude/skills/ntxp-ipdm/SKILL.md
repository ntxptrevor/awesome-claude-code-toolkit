---
name: "NTXP IPDM Environment"
description: "Integrated Project Data Management environment for NTXP. Centralizes project metadata, document indices, scope registers, and environment variables across all NTXP tools. Provides the shared data layer that NTXP Folder Structure, NTXP ID, Model Council, and Project Coda read from and write to. Use when initializing a new NTXP project environment, syncing project data across skills, or resolving cross-platform data references."
---

# NTXP IPDM Environment

## What This Skill Does

IPDM (Integrated Project Data Management) is the connective tissue between all NTXP skills. It maintains a canonical project record — metadata, document index, scope register, contact directory, and platform crosswalk — so every other NTXP skill reads from one source of truth instead of building its own silo.

## Shared Conventions

All NTXP skills follow these conventions. When in doubt, these are authoritative.

### File Paths (single source of truth)

| File | Purpose | Owner |
|------|---------|-------|
| `.ntxp/ipdm/project.yaml` | Canonical project record | IPDM (write), all skills (read) |
| `.ntxp/ipdm/identity.yaml` | Authenticated session context | NTXP ID (write), all skills (read) |
| `.ntxp/ipdm/skill-config.yaml` | Skill read/write bindings and rewiring | Auto-Deploy (write), all skills (read) |
| `.ntxp/ipdm/model-council.yaml` | Model routing configuration | Model Council (write), Highway (read) |
| `.ntxp/coda/registry.yaml` | Platform link index (read-optimized) | Coda (write from IPDM), all skills (read) |
| `.ntxp/coda/crosswalk.yaml` | Cross-platform entity map | Coda (write), all skills (read) |
| `.ntxp/coda/sync-log.jsonl` | Coda sync audit trail | Coda (append) |
| `.ntxp/highway/config.yaml` | Routing table and tier config | Highway (write), Auto-Deploy (bootstrap) |
| `.ntxp/highway/routing-log.jsonl` | Routing decision log | Highway (append) |

### Platform Keys (use these exact keys everywhere)

```yaml
platforms:
  google_drive: ""
  ebuilder: ""
  jobtread: ""
  building_connected: ""
  procore: ""
  hubspot: ""
```

All six platforms appear in every NTXP file that has a `platforms:` block. Use the exact key names above — no aliases, no abbreviations.

### Credential Resolution Chain

Every NTXP skill resolves credentials the same way:

1. **Auth** — `ntxp-id` plugin authenticates the session, writes to `.ntxp/ipdm/identity.yaml`
2. **Secrets** — `anthropic-skills:ntxp-secrets-vault` (backed by the NTXP API Keys Google Sheet) resolves API keys and tokens
3. **Never hardcode** — no credential, key, or token appears in any `.ntxp/` file or skill output

### Model Routing Protocol

When a skill needs to select an AI model:

1. **Read** `.ntxp/ipdm/model-council.yaml` for the project's model configuration
2. **Call** `anthropic-skills:ntxp-model-council` if no config exists or a new task class needs routing
3. **Log** model selection to `.ntxp/highway/routing-log.jsonl` for optimization

### Knowledge Base Protocol

Every NTXP skill follows this search-then-save pattern:

1. **Search** `.ntxp/ipdm/project.yaml` and `.ntxp/coda/registry.yaml` before any external API call
2. **Save** all outputs (documents, links, contacts, estimates) back to `.ntxp/ipdm/project.yaml`
3. **Register** all platform URLs and IDs in `.ntxp/coda/registry.yaml` and `.ntxp/coda/crosswalk.yaml`
4. **Bind** read/write paths are declared in `.ntxp/ipdm/skill-config.yaml` — check it at startup

## When to Use

- Initializing a new NTXP project workspace
- Any skill needs to look up project metadata (owner, contract, address, trades, platforms)
- Syncing state between NTXP Folder Structure, NTXP ID, Model Council, and Project Coda
- Resolving a document or record across platforms (eBuilder, JobTread, BuildingConnected, Google Drive)

## Core Data Model

### Project Record

```yaml
project:
  id: "NTXP-{YYYY}-{SEQ}"
  name: ""
  owner: ""
  contract_type: ""          # JOC | CSP | Hard Bid | CM-at-Risk | Design-Build
  cooperative: ""             # TIPS | BuyBoard | Sourcewell | Choice Partners | None
  status: ""                  # Pursuit | Pre-Con | Active | Closeout | Warranty
  platforms:
    google_drive: ""          # folder URL
    ebuilder: ""              # project URL
    jobtread: ""              # project URL
    building_connected: ""    # project URL
    procore: ""               # project URL
    hubspot: ""               # deal/contact URL
  contacts: []
  trades: []
  documents: []               # indexed by NTXP Folder Structure numbering
```

### Crosswalk

The single crosswalk lives at `.ntxp/coda/crosswalk.yaml` (owned by Coda). IPDM writes platform IDs into `project.platforms`; Coda assembles the full entity-level crosswalk from those IDs.

| Entity | google_drive | ebuilder | jobtread | building_connected | procore | hubspot |
|--------|-------------|----------|----------|-------------------|---------|---------|
| Project | Folder ID | Project ID | Job ID | Project ID | Project ID | Deal ID |
| Contact | Sheet row | Vendor ID | Contact ID | Company ID | Contact ID | Contact ID |
| Document | File ID | Document ID | File ID | Attachment ID | Doc ID | — |

## Initialization Steps

### Step 1 — Create the IPDM record

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

### Step 2 — Link to NTXP Folder Structure

When `anthropic-skills:ntxp-folder-system` runs, it writes the Google Drive folder URL back into `project.platforms.google_drive` and populates the `documents` array with the standard numbering scheme.

### Step 3 — Register with NTXP ID

NTXP ID (`ntxp-id` plugin) authenticates the user and writes session identity into `.ntxp/ipdm/identity.yaml` so all downstream skills inherit authorization context. Credentials resolve through `anthropic-skills:ntxp-secrets-vault`.

### Step 4 — Expose to other skills

All NTXP skills read `.ntxp/ipdm/project.yaml` before performing platform-specific operations, and write back any new platform IDs or document references they create. The bindings are declared in `.ntxp/ipdm/skill-config.yaml`.

## Integration Points

| Skill | Reads from IPDM | Writes to IPDM |
|-------|-----------------|----------------|
| NTXP Folder Structure | project.name, project.id | platforms.google_drive, documents[] |
| NTXP ID | — | identity.yaml (session auth) |
| NTXP Model Council | project context | model-council.yaml |
| NTXP Project Coda | all platform URLs | (writes to .ntxp/coda/ instead) |
| NTXP Highway | skill-config.yaml, model-council.yaml | routing-log.jsonl |
| NTXP Estimating | project.trades, project.contract_type | documents[], ntxp_tools refs |
| NTXP ITB Generator | project.trades, contacts[] | documents[] |
| NTXP Submittals | project.trades, documents[] | ntxp_tools.submittal_register |
| NTXP Quantity Takeoff | project.trades, documents[] | documents[] |
| BuildingConnected MCP | platforms.building_connected | platforms.building_connected, crosswalk |
| JobTread Integrator | platforms.jobtread | platforms.jobtread, crosswalk |
| eBuilder Connector | platforms.ebuilder | platforms.ebuilder, crosswalk |

## Persistence

The `.ntxp/ipdm/` directory is committed to the repo so project data survives across sessions. Sensitive values (API keys, tokens) are never stored here — those resolve through the credential chain (NTXP ID → NTXP Secrets Vault).


## NTXP Interop

This skill participates in the NTXP shared ecosystem. Follow these conventions (see NTXP IPDM skill for full spec):

- **Knowledge Base**: Search `.ntxp/ipdm/project.yaml` and `.ntxp/coda/registry.yaml` before external calls. Save outputs back to `.ntxp/ipdm/project.yaml`.
- **Credentials**: Auth via `ntxp-id` plugin → secrets via `anthropic-skills:ntxp-secrets-vault` → never hardcode.
- **Model Routing**: Read `.ntxp/ipdm/model-council.yaml` for model config. Call `ntxp-model-council` if missing.
- **Skill Bindings**: Check `.ntxp/ipdm/skill-config.yaml` for read/write path declarations.
- **Platform Keys**: Use `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot` — no aliases.
