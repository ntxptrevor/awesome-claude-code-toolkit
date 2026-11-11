# NTXP Folder Structure

Source of truth: the `ntxp-folder-system` skill. Every project uses this identical numbering. Numbers are permanent: never reused or renumbered. A deprecated folder keeps its number and gets ` - VOID` appended.

```
[Client] [Project Name]/
├── 1  - Project Knowledge Base
│    ├── 1.1  Dashboards
│    ├── 1.2  Records & Sync
│    ├── 1.3  Intake & Dossier
│    └── 1.4  Directory & Org Chart
├── 2  - Accounting
│    ├── 2.1  Contract & NTP
│    ├── 2.2  Schedule of Values
│    ├── 2.3  Pay Apps
│    ├── 2.4  Change Orders
│    ├── 2.5  Purchase Orders
│    ├── 2.6  Subcontractor Invoices
│    ├── 2.7  Insurance & Bonds
│    └── 2.8  Lien Waivers & Releases
├── 3  - Construction Docs
│    ├── 3.1  ! Current Official Set
│    ├── 3.2  Specs by Section
│    ├── 3.3  Permits
│    ├── 3.4  Addenda & ASIs
│    └── 3.5  Superseded
├── 4  - Sub Bids and ITB
│    ├── 4.1  Budget Sheets
│    ├── 4.2  ITB's
│    └── 4.3  Sub Bids   (4.3.1 - 4.3.33, see CSI table)
├── 5  - Submittals
│    ├── 5.1  Register
│    ├── 5.2  Packages by Spec Section   (cut sheets inside each section)
│    ├── 5.3  Submitted
│    └── 5.4  Approved
├── 6  - RFIs
├── 7  - Schedule
│    ├── 7.1  Current
│    ├── 7.2  Baselines & Updates
│    └── 7.3  Exports
├── 8  - OAC & Meetings
│    ├── 8.1  [dated YYYY-MM-DD subfolder per meeting]
│    └── 8.2  Recordings & Transcripts
├── 9  - Received by Client
├── 10 - Punch Lists, Daily Reports & Photos
│    ├── 10.1  Punch Lists
│    ├── 10.2  Daily Reports & Super Docs
│    ├── 10.3  Progress Photos
│    └── 10.4  Drone & 360
├── 11 - Inspections
│    ├── 11.1  AHJ
│    └── 11.2  Third-Party
├── 12 - Closeout
│    ├── 12.1  O&M & Warranties
│    ├── 12.2  As-Builts
│    ├── 12.3  Final Releases
│    └── 12.4  Final Pay App
├── 13 - HUB / MBE
│    ├── 13.1  Certifications (SBE/HUB/MBE/DBE)
│    ├── 13.2  Compliance Reports & Utilization
│    └── 13.3  Forms
└── !Public Share   (unnumbered, always public read-only)
```

## 4.3 Sub Bids: CSI subfolders (identical on every project)

| # | Name | # | Name |
|---|---|---|---|
| 4.3.1 | 01 - General Requirements | 4.3.18 | 18 - Unused |
| 4.3.2 | 02 - Existing Conditions (Demo) | 4.3.19 | 19 - Unused |
| 4.3.3 | 03 - Concrete | 4.3.20 | 20 - Unused |
| 4.3.4 | 04 - Masonry | 4.3.21 | 21 - Fire Suppression |
| 4.3.5 | 05 - Metals | 4.3.22 | 22 - Plumbing |
| 4.3.6 | 06 - Wood, Plastics, and Composites | 4.3.23 | 23 - HVAC |
| 4.3.7 | 07 - Thermal and Moisture Protection | 4.3.24 | 24 - Unused |
| 4.3.8 | 08 - Openings (Doors/Windows) | 4.3.25 | 25 - Integrated Automation |
| 4.3.9 | 09 - Finishes | 4.3.26 | 26 - Electrical |
| 4.3.10 | 10 - Specialties | 4.3.27 | 27 - Communications |
| 4.3.11 | 11 - Equipment | 4.3.28 | 28 - Electronic Safety and Security |
| 4.3.12 | 12 - Furnishings | 4.3.29 | 29 - Unused |
| 4.3.13 | 13 - Special Construction | 4.3.30 | 30 - Unused |
| 4.3.14 | 14 - Conveying Equipment | 4.3.31 | 31 - Earthwork |
| 4.3.15 | 15 - Unused | 4.3.32 | 32 - Exterior Improvements |
| 4.3.16 | 16 - Unused | 4.3.33 | Unused (catch-all outside CSI 1-32) |
| 4.3.17 | 17 - Unused | | |

Unscoped trades keep their empty folder; never delete them.

## Permissions

| Folder | Access |
|---|---|
| `!Public Share` | Always public, anyone with link, read-only |
| Everything else (1-13 and subfolders) | NTXP employee-only, read/write |

Claude cannot change Drive sharing. Flag to a human with Drive admin rights and document exceptions in `_PERMISSIONS.md` at the project root.

## Where outputs go

| Output | Folder |
|---|---|
| Dashboards, command center | 1.1 |
| Owner Insite / PM Web / JobTread pulls | 1.2 |
| OCR dossiers, canonical project model | 1.3 |
| Directory, org chart | 1.4 |
| Contracts, NTP / SOV / Pay apps / Change orders | 2.1 / 2.2 / 2.3 / 2.4 |
| Active estimating drafts after award | 4.1 |
| Submittal register / packages / submitted / approved | 5.1 / 5.2 / 5.3 / 5.4 |
| RFIs | 6 |
| CPM and Gantt exports | 7.1 / 7.3 |
| OAC agendas, minutes (dated subfolder) / recordings | 8.1 / 8.2 |
| Owner correspondence, formal client submissions | 9 |
| Punch lists / daily reports / photos / drone | 10.1 / 10.2 / 10.3 / 10.4 |
| Inspections | 11.1 / 11.2 |
| Closeout, warranties, as-builts, final pay app | 12.x |
| HUB/MBE certifications, utilization, forms | 13.x |

If an output type isn't listed, use the closest match and note the gap. Do not add a root-level folder without checking with Trevor.

## Numbering note (needs confirmation)

Council decision C-261005-11B0 (folder structure v1.2, 2026-10-05) says "retain 0 - Knowledge Base" and Forge Coda stores records under `0.2 Structured Data`. The current `ntxp-folder-system` skill numbers roots from 1 (`1 - Project Knowledge Base`, `1.2 Records & Sync`). This skill follows `ntxp-folder-system` because it states it is canonical. If the owner confirms v1.2 numbering instead, change this file once; nothing else hard-codes the number.

The same decision requires quarantine-before-move, a copy-only dry run, and human review of uncertain classifications before any live sorting. Project Init only creates folders and never moves files, so it does not trigger that rule.

## Rules

- **Submittals (5.x)**: each stage change drops a dated copy in that stage's folder; never overwrite.
- **First-look locations**: bids in `NTXP PM > !Active Bids`; awarded projects in `NTXP > !Active Projects`; standard documents in `!Company Documents`.
- **Triage loop**: detect, classify, relocate only high-confidence files within the same project, handle revisions in dated subfolders, flag obsolete files ` - VOID` in place, log to `_Triage Log`. Never delete, never leave the project tree, never guess.
- **Legacy projects**: merge duplicate folders (two "Change Orders" become 2.4), move HUB/MBE out of Accounting into 13, keep historical dated folder names.
