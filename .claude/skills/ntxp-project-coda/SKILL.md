---
name: "NTXP Project Coda"
description: "Centralized project link registry and platform crosswalk for NTXP. Aggregates URLs, credentials references, and access points across Google Drive, eBuilder, JobTread, BuildingConnected, Procore, HubSpot, and all NTXP tools into a single navigable index. Use when setting up a new project, auditing platform access, generating a project handoff package, or when any skill needs to resolve a cross-platform reference."
---

# NTXP Project Coda

## What This Skill Does

Project Coda is NTXP's master link registry. Every platform, tool, folder, dashboard, and integration point for a project is cataloged here with live URLs, access status, and the crosswalk that maps one platform's ID to another. It is the "table of contents" for a project's digital footprint.

## When to Use

- Setting up a new NTXP project — Coda collects all links after other skills create them
- Handing off a project to a new team member — generate the full access map
- Auditing which platforms are connected and which are missing
- Any skill needs to look up a platform URL for the current project
- Generating OAC meeting prep or project status dashboards

## Core Registry Structure

### Project Link Index

```yaml
coda:
  project_id: "NTXP-{YYYY}-{SEQ}"
  project_name: ""
  last_updated: ""
  
  platforms:
    google_drive:
      url: ""
      status: ""          # connected | pending | not-applicable
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

### Platform Crosswalk Matrix

Maps the same real-world entity across every system:

```yaml
crosswalk:
  - entity: "Main Project"
    google_drive: "{folder_id}"
    ebuilder: "{project_id}"
    jobtread: "{job_id}"
    building_connected: "{project_id}"
    
  - entity: "GC Contact - NTXP"
    google_drive: "{contact_sheet_row}"
    ebuilder: "{vendor_id}"
    jobtread: "{contact_id}"
    building_connected: "{company_id}"
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
crosswalk: []
YAML
```

### Step 2 — Pull from IPDM

If `.ntxp/ipdm/project.yaml` exists, read platform URLs from it and populate the registry. IPDM is the write source; Coda is the read-optimized index.

### Step 3 — Validate Links

For each platform entry with a URL, verify it resolves (HTTP HEAD or API ping). Mark status as `connected` or `unreachable`.

### Step 4 — Generate Summary Card

Output a formatted project access card:

```
+==========================================+
|       PROJECT CODA — {Project Name}      |
+==========================================+
| Google Drive   | [link] | connected      |
| eBuilder       | [link] | connected      |
| JobTread       | [link] | pending        |
| BuildingConn.  | [link] | connected      |
| HubSpot        | [link] | connected      |
+------------------------------------------+
| NTXP Tools                               |
| Estimating     | [link]                  |
| Submittals     | [link]                  |
| Bid Dashboard  | [link]                  |
+------------------------------------------+
| Team Access                              |
| Trevor (PM)    | All platforms           |
| ...                                      |
+==========================================+
```

## Integration Points

| Skill | How Coda Interacts |
|-------|--------------------|
| NTXP IPDM | Reads platform URLs from IPDM, syncs back validation status |
| NTXP Folder Structure | Receives Google Drive folder URL after creation |
| NTXP ID | Receives authenticated user context for access checks |
| NTXP Highway | Coda is called at end of project setup chains |
| NTXP Estimating | Registers estimating workspace links |
| OAC Dashboard | Coda feeds the project links section |

## Persistence

The `.ntxp/coda/` directory is committed to the repo. Updates are append-friendly — each sync adds a timestamped entry to `.ntxp/coda/sync-log.jsonl` for audit trail.
