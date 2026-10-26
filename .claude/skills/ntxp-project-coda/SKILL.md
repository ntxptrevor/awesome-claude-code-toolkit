---
name: "NTXP Project Coda"
description: "Centralized project link registry and platform crosswalk for NTXP. Aggregates URLs, credentials references, and access points across Google Drive, eBuilder, JobTread, BuildingConnected, Procore, HubSpot, and all NTXP tools into a single navigable index. Use when setting up a new project, auditing platform access, generating a project handoff package, or when any skill needs to resolve a cross-platform reference."
---

# NTXP Project Coda

## What This Skill Does

Project Coda is NTXP's master link registry. Every platform, tool, folder, dashboard, and integration point for a project is cataloged here with live URLs, access status, and the crosswalk that maps one platform's ID to another. It is the "table of contents" for a project's digital footprint.

## Shared Conventions

Coda follows the NTXP shared conventions defined in the NTXP IPDM skill. Key references:

| Convention | Source |
|-----------|--------|
| File paths | `.ntxp/coda/registry.yaml` (links), `.ntxp/coda/crosswalk.yaml` (entity map), `.ntxp/coda/sync-log.jsonl` (audit) |
| Platform keys | `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot` |
| Credential chain | `ntxp-id` → `ntxp-secrets-vault` → never hardcode |
| Model routing | Read `.ntxp/ipdm/model-council.yaml` for model config if needed |
| Knowledge base | Read from `.ntxp/ipdm/project.yaml` (source of truth) → write to `.ntxp/coda/` (read-optimized index) |
| Skill bindings | Coda's bindings declared in `.ntxp/ipdm/skill-config.yaml` |

## When to Use

- Setting up a new NTXP project — Coda collects all links after other skills create them
- Handing off a project to a new team member — generate the full access map
- Auditing which platforms are connected and which are missing
- Any skill needs to look up a platform URL for the current project
- Generating OAC meeting prep or project status dashboards

## Core Registry Structure

### Project Link Index

Uses the **six standard platform keys** from NTXP conventions:

```yaml
coda:
  project_id: "NTXP-{YYYY}-{SEQ}"
  project_name: ""
  last_updated: ""
  
  platforms:
    google_drive:
      url: ""
      status: ""          # connected | pending | unreachable | not-applicable
      folder_id: ""
    ebuilder:
      url: ""
      status: ""
      project_id: ""
    jobtread:
      url: ""
      status: ""
      job_id: ""
    building_connected:
      url: ""
      status: ""
      project_id: ""
    procore:
      url: ""
      status: ""
      project_id: ""
    hubspot:
      url: ""
      status: ""
      deal_id: ""
    
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
    
  team:
    - name: ""
      role: ""
      email: ""
      platforms: []        # which platforms they have access to
```

### Platform Crosswalk (single source of truth)

The crosswalk lives **only** at `.ntxp/coda/crosswalk.yaml`. No other file duplicates it. All skills that need entity-level cross-platform resolution read from here.

```yaml
crosswalk:
  - entity: "Main Project"
    google_drive: "{folder_id}"
    ebuilder: "{project_id}"
    jobtread: "{job_id}"
    building_connected: "{project_id}"
    procore: "{project_id}"
    hubspot: "{deal_id}"
    
  - entity: "GC Contact - NTXP"
    google_drive: "{contact_sheet_row}"
    ebuilder: "{vendor_id}"
    jobtread: "{contact_id}"
    building_connected: "{company_id}"
    procore: "{contact_id}"
    hubspot: "{contact_id}"
```

## Initialization Steps

### Step 1 — Create Coda Registry

```bash
mkdir -p .ntxp/coda
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
  ntxp_tools: {}
  external: {}
  team: []
YAML
cat > .ntxp/coda/crosswalk.yaml << 'YAML'
crosswalk: []
YAML
touch .ntxp/coda/sync-log.jsonl
```

### Step 2 — Pull from IPDM

Read `.ntxp/ipdm/project.yaml` and populate the registry. IPDM is the write source; Coda is the read-optimized index. Copy platform URLs, project ID, and project name.

### Step 3 — Authenticate via NTXP ID

Before validating external links, check `.ntxp/ipdm/identity.yaml` for active session auth. If no identity file exists, invoke `ntxp-id` first. Credentials for platform API calls resolve through `anthropic-skills:ntxp-secrets-vault`.

### Step 4 — Validate Links

For each platform entry with a URL, verify it resolves (HTTP HEAD or API ping via the appropriate MCP connector). Mark status as `connected`, `unreachable`, or `not-applicable`. Log each check to `.ntxp/coda/sync-log.jsonl`.

### Step 5 — Build Crosswalk

For each connected platform, extract entity IDs and populate `.ntxp/coda/crosswalk.yaml` with the entity-level map.

### Step 6 — Generate Summary Card

Output a formatted project access card:

```
+=====================================================+
|       PROJECT CODA — {Project Name}                 |
|       ID: {NTXP-YYYY-SEQ}                          |
+=====================================================+
| Platform         | URL          | Status            |
|------------------|--------------|-------------------|
| Google Drive     | [link]       | connected         |
| eBuilder         | [link]       | connected         |
| JobTread         | [link]       | pending           |
| BuildingConn.    | [link]       | connected         |
| Procore          | —            | not-applicable    |
| HubSpot          | [link]       | connected         |
+-----------------------------------------------------+
| NTXP Tools                                          |
| Estimating       | [link]                           |
| Submittals       | [link]                           |
| Bid Dashboard    | [link]                           |
| SOV              | [link]                           |
+-----------------------------------------------------+
| Team Access                                         |
| Trevor (PM)      | All platforms                    |
| ...                                                 |
+-----------------------------------------------------+
| Crosswalk: {N} entities mapped                      |
| Auth: ntxp-id active | Secrets: ntxp-secrets-vault  |
+=====================================================+
```

## Integration Points

| Skill | How Coda Interacts | Shared File |
|-------|--------------------|-------------|
| NTXP IPDM | Reads platform URLs from `.ntxp/ipdm/project.yaml` | project.yaml |
| NTXP Folder Structure | Receives Google Drive folder URL after creation | project.yaml → registry.yaml |
| NTXP ID | Reads `.ntxp/ipdm/identity.yaml` for auth context | identity.yaml |
| NTXP Highway | Coda is called at end of project setup chains | skill-config.yaml bindings |
| NTXP Model Council | Reads model config for any AI-assisted validation | model-council.yaml |
| NTXP Estimating | Registers estimating workspace links | registry.yaml |
| OAC Dashboard | Coda feeds the project links section | registry.yaml |
| BuildingConnected MCP | Writes platform IDs to crosswalk | crosswalk.yaml |
| JobTread Integrator | Writes platform IDs to crosswalk | crosswalk.yaml |
| eBuilder Connector | Writes platform IDs to crosswalk | crosswalk.yaml |

## Persistence

The `.ntxp/coda/` directory is committed to the repo. Updates are append-friendly — each sync adds a timestamped entry to `.ntxp/coda/sync-log.jsonl` for audit trail. Credentials are never stored here — they resolve through the standard credential chain (ntxp-id → ntxp-secrets-vault).
