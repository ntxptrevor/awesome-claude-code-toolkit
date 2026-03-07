# Construction Submittal Tracker

CLI tool for JOC (Job Order Contracting) and public construction submittal management. Tracks submittals by CSI MasterFormat division and trade, with lead time tracking and critical path identification.

## Quick Start

```bash
# 1. Initialize a project register
python submittal_tracker.py init "My Project" --contract-no "JOC-2026-001"

# 2. Generate submittals from CSI reference data (all divisions or selected)
python submittal_tracker.py generate
python submittal_tracker.py generate --divisions=03,05,08,23,26

# 3. View the dashboard
python submittal_tracker.py dashboard

# 4. Update submittal statuses as work progresses
python submittal_tracker.py update 05-001 --status "Submitted" --date-submitted "2026-03-01"
python submittal_tracker.py update 05-001 --status "Approved" --date-returned "2026-03-15"

# 5. View filtered lists
python submittal_tracker.py list --critical          # Long-lead items not yet approved
python submittal_tracker.py list --division 26       # Electrical only
python submittal_tracker.py list --trade "HVAC"      # By trade
python submittal_tracker.py list --status "Submitted" # By status

# 6. Generate reports
python submittal_tracker.py report                    # Text report
python submittal_tracker.py report --format csv       # CSV export
```

## Scanning Specifications

```bash
# Scan a spec file for submittal requirements
python submittal_tracker.py scan path/to/specs.txt

# Import the scan results into your register
python submittal_tracker.py import-spec scan_results_specs.json
```

## Commands

| Command | Description |
|---------|-------------|
| `init` | Create a new submittal register for a project |
| `generate` | Populate register from built-in CSI reference data |
| `scan` | Parse a specification file to extract submittal requirements |
| `import-spec` | Import scan results into the active register |
| `add` | Manually add a single submittal |
| `list` | View submittals with filters (status, division, trade, critical) |
| `update` | Change status, lead time, dates, or notes on a submittal |
| `dashboard` | Visual summary with status counts, division breakdown, critical path |
| `report` | Generate full register report (text or CSV) |

## Submittal Statuses

| Symbol | Status | Meaning |
|--------|--------|---------|
| `[ ]` | Not Started | Submittal identified, not yet in preparation |
| `[~]` | In Preparation | Trade/sub preparing the submittal |
| `[>]` | Submitted | Sent to A/E for review |
| `[?]` | Under Review | A/E actively reviewing |
| `[+]` | Approved | No exceptions |
| `[*]` | Approved as Noted | Approved with minor comments |
| `[!]` | Revise & Resubmit | Requires correction and resubmission |
| `[X]` | Rejected | Not acceptable, start over |
| `[R]` | For Record Only | Informational, no approval needed |
| `[=]` | Closed | Final disposition complete |

## Submittal Types

| Code | Type |
|------|------|
| SD | Shop Drawings |
| PD | Product Data |
| SS | Samples |
| CP | Certificates/Permits |
| DI | Design Information |
| MO | Mockups |
| QC | Quality Control |
| CL | Closeout |
| WP | Work Plan |
| SR | Sustainable/LEED |

## CSI Divisions Covered

Divisions 01-33 with trade-specific submittals and typical lead times pre-loaded. See `data/csi_submittal_types.json` for the complete reference dataset.

## Output Files

- `submittal_register.json` — Machine-readable register (primary data store)
- `submittal_register.csv` — Auto-exported CSV for spreadsheet use
- `scan_results_*.json` — Spec scan output for review before import

## Requirements

- Python 3.7+
- No external dependencies (stdlib only)
