# Project Coda (absorbed)

Coda is the project's link registry and cross-platform crosswalk: one place that records every platform, folder, dashboard and portal for a project, with status, and maps one real-world entity to its id on each platform. IPDM is the write source; Coda is the read-optimized index. All Coda files are written by Project Init.

## Provenance and reconciliation

This is the local workflow. A separate Forge skill, `ntxp-project-coda` v1.0.0 (engine `scripts/coda.py`), is listed on council tab 23 as "proposed, pending ratification" with a wider scope: QuickBooks, JobTread, Drive, owner platforms, planrooms and portals, a project biography, JEV-assisted confidence grading (capped), storage in the Drive Structured Data KB with a JobTread mirror, and a Lightfield note/plan step. Its files were not available when this was merged, so none of that logic is copied here.

- Installed: delegate biography, confidence grading and the Lightfield step to it; this file keeps the registry and crosswalk.
- Not installed: everything below still works standalone.
- Open items to reconcile once its source is available: add a `quickbooks` platform key (the six-key convention is platform-agnostic otherwise); the Forge Coda stores its KB under `0.2 Structured Data`, but the current folder tree puts records under `1.2 Records & Sync` (see the numbering note in `folder-structure.md`).

## Files

| File | Purpose |
|---|---|
| `.ntxp/coda/registry.yaml` | Platform and tool link index with status |
| `.ntxp/coda/crosswalk.yaml` | Entity-level id map across platforms (the only crosswalk) |
| `.ntxp/coda/sync-log.jsonl` | Append-only audit of every validation or sync |

No credentials in any of these. Credentials resolve through NTXP ID then the vault.

## registry.yaml

```yaml
coda:
  project_id: ""              # NTXP-{YYYY}-{SEQ}
  project_name: ""
  last_updated: ""
  platforms:                  # exactly these six keys
    google_drive:       { url: "", status: "pending", folder_id: "" }
    ebuilder:           { url: "", status: "pending", project_id: "" }
    jobtread:           { url: "", status: "pending", job_id: "" }
    building_connected: { url: "", status: "pending", project_id: "" }
    procore:            { url: "", status: "not-applicable", project_id: "" }
    hubspot:            { url: "", status: "pending", deal_id: "" }
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
    planroom: ""
    quickbooks: ""
  team:                       # who has access to what
    - { name: "", role: "", email: "", platforms: [] }
```

Status values: `connected | pending | unreachable | not-applicable`.

## crosswalk.yaml

```yaml
crosswalk:
  - entity: "Main Project"
    google_drive: ""          # folder id
    ebuilder: ""              # project id
    jobtread: ""              # job id
    building_connected: ""    # project id
    procore: ""               # project id
    hubspot: ""               # deal id
  - entity: "Contact: <name>"
    google_drive: ""          # contact sheet row
    ebuilder: ""              # vendor id
    jobtread: ""              # contact id
    building_connected: ""    # company id
    procore: ""               # contact id
    hubspot: ""               # contact id
```

Entity types: project, contact, document (document ids: Drive file id, eBuilder document id, JobTread file id, BuildingConnected attachment id).

## Operations

### Build (part of `create`, Step 5)

1. Create the three files if missing (empty registry with the statuses above, `crosswalk: []`, empty log).
2. Pull from IPDM: copy project id, name and every platform URL from `.ntxp/ipdm/project.yaml`.
3. Confirm identity (`.ntxp/ipdm/identity.yaml`); if missing, run the NTXP ID step first.
4. Validate (below), then build the crosswalk from the ids each connected platform returns.
5. Print the access card.

### Validate

For each registry entry with a URL, check it resolves through the matching connector (API ping or HTTP HEAD), set the status, and append one JSON line to `sync-log.jsonl`:

```json
{"ts":"<UTC ISO>","platform":"jobtread","url":"<url>","result":"connected","by":"ntxp-project-init"}
```

Never mark `connected` without a call that returned success. An entry with no URL stays `pending`.

### Audit (mode `audit`)

Read-only. List each platform with its status, which are `pending` or `unreachable`, which team members lack access to which platform, and the crosswalk gaps (an entity present on one platform but missing on another). Report; do not fix without asking.

### Handoff (mode `handoff`)

Produce the project access map for a new team member: the access card, the team table with the platforms each person needs, the folder tree location, and the open items. Send only what the recipient is entitled to see; leave out credentials and anything under `13 HUB / MBE` or `2 Accounting` unless the recipient's role requires it.

### Resolve (mode `resolve`)

Read-only lookup for other skills: given an entity or platform, return the URL or id from the registry or crosswalk. If absent, say so; never guess an id.

### Sync

When another skill creates a link or id (a Drive folder, a JobTread job, a BuildingConnected project), write it to IPDM `platforms.*`, then to the registry and crosswalk, then log it. IPDM first, Coda second.

## Access card

```
+=====================================================+
|  PROJECT CODA - {Project Name}                      |
|  ID: {NTXP-YYYY-SEQ}                                |
+=====================================================+
| Platform           | Link        | Status           |
|--------------------|-------------|------------------|
| Google Drive       | [link]      | connected        |
| eBuilder           | [link]      | pending          |
| JobTread           | [link]      | connected        |
| BuildingConnected  | [link]      | connected        |
| Procore            | -           | not-applicable   |
| HubSpot            | [link]      | connected        |
+-----------------------------------------------------+
| NTXP tools: estimating, submittals, bid dashboard,  |
|             SOV, daily reports                      |
| Team: {N} people, access per platform listed below  |
| Crosswalk: {N} entities mapped                      |
| Identity: {verified|unverified} | Credentials: vault |
+=====================================================+
```

## Interactions

| Skill | How it uses Coda |
|---|---|
| NTXP folder system | Receives the Drive folder URL after creation, written to IPDM then Coda |
| NTXP ID | Provides identity before any validation |
| Forge `ntxp-highway`, `ntxp-model-router` | Call `resolve` for URLs and ids |
| Estimating, ITB, submittals | Register workspace and register links |
| OAC dashboard | Reads the links section |
| BuildingConnected, JobTread, eBuilder connectors | Write platform ids to the crosswalk |
