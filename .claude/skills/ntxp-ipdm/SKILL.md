---
name: "NTXP IPDM Environment"
description: "Integrated Project Data Management environment for NTXP. Centralizes project metadata, document indices, scope registers, and environment variables across all NTXP tools. Provides the shared data layer that NTXP Folder Structure, NTXP ID, Model Council, and Project Coda read from and write to. Use when initializing a new NTXP project environment, syncing project data across skills, or resolving cross-platform data references."
---

# NTXP IPDM Environment

## What This Skill Does

IPDM (Integrated Project Data Management) is the connective tissue between all NTXP skills. It maintains a canonical project record — metadata, document index, scope register, contact directory, and platform crosswalk — so every other NTXP skill reads from one source of truth instead of building its own silo.

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
    procore: ""               # project URL (if applicable)
  contacts: []
  trades: []
  documents: []               # indexed by NTXP Folder Structure numbering
```

### Platform Crosswalk

Maps the same entity (project, contact, document) across every platform NTXP uses:

| Entity | Google Drive | eBuilder | JobTread | BuildingConnected |
|--------|-------------|----------|----------|-------------------|
| Project | Folder ID | Project ID | Job ID | Project ID |
| Contact | Contact Sheet row | Vendor ID | Contact ID | Company ID |
| Document | File ID | Document ID | File ID | Attachment ID |

## Initialization Steps

### Step 1 — Create the IPDM record

```bash
mkdir -p .ntxp/ipdm
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
  contacts: []
  trades: []
  documents: []
YAML
```

### Step 2 — Link to NTXP Folder Structure

When `anthropic-skills:ntxp-folder-system` runs, it writes the Google Drive folder URL back into `project.platforms.google_drive` and populates the `documents` array with the standard numbering scheme.

### Step 3 — Register with NTXP ID

NTXP ID (`ntxp-id` plugin) authenticates the user and writes session identity into `.ntxp/ipdm/identity.yaml` so all downstream skills inherit authorization context.

### Step 4 — Expose to other skills

All NTXP skills should read `.ntxp/ipdm/project.yaml` before performing platform-specific operations, and write back any new platform IDs or document references they create.

## Integration Points

| Skill | Reads | Writes |
|-------|-------|--------|
| NTXP Folder Structure | project.name, project.id | platforms.google_drive, documents[] |
| NTXP ID | — | identity.yaml (session auth) |
| NTXP Model Council | project context for model routing | model selection logs |
| NTXP Project Coda | all platform URLs | link validation status |
| NTXP Estimating | project.trades, project.contract_type | estimate references |
| NTXP ITB Generator | project.trades, contacts | ITB document refs |

## Persistence

The `.ntxp/ipdm/` directory is committed to the repo so project data survives across sessions. Sensitive values (API keys, tokens) are never stored here — those live in NTXP Secrets Vault.
