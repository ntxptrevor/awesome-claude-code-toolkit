#!/usr/bin/env python3
"""
Construction Submittal Tracker
==============================
CLI tool for JOC and public construction submittal management.
Scans specs, generates registers, tracks lead times, and manages approvals.

Usage:
    python submittal_tracker.py init <project_name> [--contract-no=<num>]
    python submittal_tracker.py scan <spec_file>
    python submittal_tracker.py generate [--divisions=<divs>]
    python submittal_tracker.py add --desc=<desc> --div=<div> --type=<type> [--spec=<sec>] [--trade=<trade>] [--lead=<weeks>]
    python submittal_tracker.py list [--status=<status>] [--division=<div>] [--trade=<trade>] [--critical]
    python submittal_tracker.py update <submittal_id> [--status=<status>] [--lead=<weeks>] [--notes=<notes>] [--date-submitted=<date>] [--date-returned=<date>]
    python submittal_tracker.py report [--format=<fmt>]
    python submittal_tracker.py dashboard
    python submittal_tracker.py import-spec <scan_output>
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

TOOL_DIR = Path(__file__).parent
DATA_DIR = TOOL_DIR / "data"
CSI_DATA_FILE = DATA_DIR / "csi_submittal_types.json"

REGISTER_FILENAME = "submittal_register.json"
REGISTER_CSV = "submittal_register.csv"

VALID_STATUSES = [
    "Not Started",
    "In Preparation",
    "Submitted",
    "Under Review",
    "Approved",
    "Approved as Noted",
    "Revise & Resubmit",
    "Rejected",
    "For Record Only",
    "Closed",
]

STATUS_SYMBOLS = {
    "Not Started": "[ ]",
    "In Preparation": "[~]",
    "Submitted": "[>]",
    "Under Review": "[?]",
    "Approved": "[+]",
    "Approved as Noted": "[*]",
    "Revise & Resubmit": "[!]",
    "Rejected": "[X]",
    "For Record Only": "[R]",
    "Closed": "[=]",
}


def load_csi_data():
    with open(CSI_DATA_FILE) as f:
        return json.load(f)


def get_register_path():
    return Path.cwd() / REGISTER_FILENAME


def load_register():
    path = get_register_path()
    if not path.exists():
        print(f"Error: No submittal register found in {Path.cwd()}")
        print("Run 'submittal_tracker.py init <project_name>' first.")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def save_register(register):
    path = get_register_path()
    with open(path, "w") as f:
        json.dump(register, f, indent=2, default=str)
    export_csv(register)


def export_csv(register):
    """Export register to CSV for spreadsheet compatibility."""
    csv_path = Path.cwd() / REGISTER_CSV
    if not register.get("submittals"):
        return
    fieldnames = [
        "id", "number", "spec_section", "division", "division_name", "trade",
        "description", "type_code", "type_name", "status", "lead_time_weeks",
        "date_required", "date_submitted", "date_returned", "disposition",
        "resubmittal_count", "notes", "created", "updated",
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for sub in register["submittals"]:
            row = {**sub}
            writer.writerow(row)


def next_submittal_number(register, division):
    """Generate next submittal number: DIV-NNN format."""
    existing = [s for s in register["submittals"] if s["division"] == division]
    seq = len(existing) + 1
    return f"{division}-{seq:03d}"


# ─── Commands ──────────────────────────────────────────────────────────────────


def cmd_init(args):
    """Initialize a new submittal register for a project."""
    path = get_register_path()
    if path.exists() and not args.force:
        print(f"Register already exists at {path}")
        print("Use --force to overwrite.")
        return

    register = {
        "project": {
            "name": args.project_name,
            "contract_number": args.contract_no or "",
            "created": datetime.now().isoformat(),
            "owner": "",
            "architect": "",
            "contractor": "",
        },
        "submittals": [],
        "metadata": {
            "next_id": 1,
            "version": "1.0",
            "tool": "construction-submittal-tracker",
        },
    }
    save_register(register)
    print(f"Initialized submittal register for: {args.project_name}")
    print(f"  File: {path}")
    if args.contract_no:
        print(f"  Contract: {args.contract_no}")
    print("\nNext steps:")
    print("  - Run 'generate' to populate from CSI reference data")
    print("  - Run 'scan <spec_file>' to extract from project specs")
    print("  - Run 'add' to manually add individual submittals")


def cmd_generate(args):
    """Generate submittals from CSI reference data for selected divisions."""
    register = load_register()
    csi = load_csi_data()

    if args.divisions:
        selected = [d.strip().zfill(2) for d in args.divisions.split(",")]
    else:
        selected = list(csi["divisions"].keys())

    count = 0
    for div_code in selected:
        if div_code not in csi["divisions"]:
            print(f"Warning: Division {div_code} not found in reference data, skipping.")
            continue

        div = csi["divisions"][div_code]
        for item in div["common_submittals"]:
            sub_id = register["metadata"]["next_id"]
            sub_number = next_submittal_number(register, div_code)
            type_info = csi["submittal_types"].get(item["type"], {})

            submittal = {
                "id": sub_id,
                "number": sub_number,
                "spec_section": f"{div_code} 00 00",
                "division": div_code,
                "division_name": div["name"],
                "trade": div["trade"],
                "description": item["description"],
                "type_code": item["type"],
                "type_name": type_info.get("name", ""),
                "status": "Not Started",
                "lead_time_weeks": item["lead_weeks"],
                "date_required": "",
                "date_submitted": "",
                "date_returned": "",
                "disposition": "",
                "resubmittal_count": 0,
                "notes": "",
                "created": datetime.now().isoformat(),
                "updated": datetime.now().isoformat(),
            }
            register["submittals"].append(submittal)
            register["metadata"]["next_id"] = sub_id + 1
            count += 1

    save_register(register)
    print(f"Generated {count} submittals across {len(selected)} divisions.")
    print(f"Register now contains {len(register['submittals'])} total submittals.")


def cmd_scan(args):
    """Scan a specification file to extract submittal requirements."""
    spec_path = Path(args.spec_file)
    if not spec_path.exists():
        print(f"Error: File not found: {spec_path}")
        sys.exit(1)

    content = spec_path.read_text(errors="replace")
    csi = load_csi_data()

    # Patterns that commonly indicate submittal requirements in specs
    submittal_patterns = [
        r"(?i)(?:submit|furnish|provide|deliver)\s+(?:the\s+following\s+)?(?:shop\s+drawings?)",
        r"(?i)(?:submit|furnish|provide|deliver)\s+(?:the\s+following\s+)?(?:product\s+data)",
        r"(?i)(?:submit|furnish|provide|deliver)\s+(?:the\s+following\s+)?(?:samples?)",
        r"(?i)(?:submit|furnish|provide|deliver)\s+(?:the\s+following\s+)?(?:certificates?)",
        r"(?i)(?:submit|furnish|provide|deliver)\s+(?:the\s+following\s+)?(?:test\s+reports?)",
        r"(?i)(?:submit|furnish|provide|deliver)\s+(?:the\s+following\s+)?(?:mix\s+designs?)",
        r"(?i)(?:submit|furnish|provide|deliver)\s+(?:the\s+following\s+)?(?:manufacturer.s?\s+data)",
        r"(?i)(?:submit|furnish|provide|deliver)\s+(?:the\s+following\s+)?(?:warranty|warrantee)",
        r"(?i)(?:submit|furnish|provide|deliver)\s+(?:the\s+following\s+)?(?:mock.?ups?)",
        r"(?i)(?:submit|furnish|provide|deliver)\s+(?:the\s+following\s+)?(?:o\s*&\s*m\s+manuals?)",
        r"(?i)(?:submit|furnish|provide|deliver)\s+(?:the\s+following\s+)?(?:as.?built)",
        r"(?i)(?:submit|furnish|provide|deliver)\s+(?:the\s+following\s+)?(?:closeout)",
        r"(?i)(?:submit|furnish|provide|deliver)\s+(?:the\s+following\s+)?(?:design\s+(?:data|calculations?))",
        r"(?i)(?:submit|furnish|provide|deliver)\s+(?:the\s+following\s+)?(?:work\s+plan)",
        r"(?i)(?:submit|furnish|provide|deliver)\s+(?:the\s+following\s+)?(?:safety\s+plan)",
        r"(?i)section\s+(\d{2})\s*(\d{2})\s*(\d{2})",
        r"(?i)PART\s+1\s*[-–]\s*SUBMITTALS",
        r"(?i)1\.\d+\s+SUBMITTALS",
    ]

    # Extract spec section numbers
    section_matches = re.findall(r"(?i)section\s+(\d{2})\s*(\d{2})\s*(\d{2})", content)
    found_divisions = set()
    for match in section_matches:
        found_divisions.add(match[0])

    # Extract submittal items by context
    found_submittals = []
    lines = content.split("\n")

    in_submittal_section = False
    current_section = ""
    current_division = ""

    for i, line in enumerate(lines):
        # Detect spec section headers
        sec_match = re.match(r"(?i)(?:SECTION\s+)?(\d{2})\s*(\d{2})\s*(\d{2})", line)
        if sec_match:
            current_section = f"{sec_match.group(1)} {sec_match.group(2)} {sec_match.group(3)}"
            current_division = sec_match.group(1)

        # Detect submittal section
        if re.search(r"(?i)SUBMITTALS|SUBMITTAL\s+REQUIREMENTS", line):
            in_submittal_section = True
            continue

        if in_submittal_section and re.match(r"(?i)\s*(PART\s+[23]|^\d+\.\d+\s+(?!SUBMITTALS))", line):
            in_submittal_section = False

        if in_submittal_section:
            # Look for submittal item descriptions
            for pattern_name, type_code in [
                (r"(?i)shop\s+drawings?", "SD"),
                (r"(?i)product\s+data", "PD"),
                (r"(?i)samples?", "SS"),
                (r"(?i)certificates?", "CP"),
                (r"(?i)test\s+reports?", "QC"),
                (r"(?i)mix\s+designs?", "DI"),
                (r"(?i)mock.?ups?", "MO"),
                (r"(?i)o\s*&\s*m\s+manuals?", "CL"),
                (r"(?i)warran(?:ty|tee|ties)", "CL"),
                (r"(?i)as.?built", "CL"),
                (r"(?i)work\s+plan|method\s+statement", "WP"),
                (r"(?i)safety\s+plan|HASP", "WP"),
                (r"(?i)design\s+(?:data|calc)", "DI"),
            ]:
                if re.search(pattern_name, line):
                    desc = line.strip()
                    # Clean up the description
                    desc = re.sub(r"^[A-Z]\.\s*", "", desc)
                    desc = re.sub(r"^\d+\.\s*", "", desc)
                    desc = re.sub(r"^[-•]\s*", "", desc)
                    desc = desc.strip()
                    if len(desc) > 10:
                        found_submittals.append({
                            "description": desc[:120],
                            "type_code": type_code,
                            "spec_section": current_section,
                            "division": current_division,
                        })
                    break

    # Also match by division reference data for found divisions
    enriched = []
    for sub in found_submittals:
        div = sub["division"]
        if div in csi["divisions"]:
            div_info = csi["divisions"][div]
            sub["trade"] = div_info["trade"]
            sub["division_name"] = div_info["name"]
            # Try to match lead time from reference
            sub["lead_time_weeks"] = 4  # default
            for ref in div_info["common_submittals"]:
                if sub["type_code"] == ref["type"]:
                    sub["lead_time_weeks"] = ref["lead_weeks"]
                    break
        else:
            sub["trade"] = "TBD"
            sub["division_name"] = f"Division {div}"
            sub["lead_time_weeks"] = 4
        enriched.append(sub)

    # Output scan results
    output_path = Path.cwd() / f"scan_results_{spec_path.stem}.json"
    scan_result = {
        "source_file": str(spec_path),
        "scan_date": datetime.now().isoformat(),
        "divisions_found": sorted(found_divisions),
        "submittals_found": len(enriched),
        "items": enriched,
    }
    with open(output_path, "w") as f:
        json.dump(scan_result, f, indent=2)

    print(f"Spec Scan Results: {spec_path.name}")
    print(f"{'=' * 60}")
    print(f"Divisions detected: {', '.join(sorted(found_divisions)) or 'None'}")
    print(f"Submittal items found: {len(enriched)}")
    print()

    if enriched:
        print(f"{'Type':<6} {'Division':<8} {'Description':<50}")
        print(f"{'-'*6} {'-'*8} {'-'*50}")
        for item in enriched:
            print(f"{item['type_code']:<6} {item.get('division', 'N/A'):<8} {item['description'][:50]}")

    print(f"\nResults saved to: {output_path}")
    print(f"Run 'import-spec {output_path}' to add these to your register.")


def cmd_import_spec(args):
    """Import scan results into the register."""
    scan_path = Path(args.scan_output)
    if not scan_path.exists():
        print(f"Error: File not found: {scan_path}")
        sys.exit(1)

    with open(scan_path) as f:
        scan = json.load(f)

    register = load_register()
    csi = load_csi_data()
    count = 0

    for item in scan["items"]:
        sub_id = register["metadata"]["next_id"]
        div = item.get("division", "01")
        sub_number = next_submittal_number(register, div)
        type_info = csi["submittal_types"].get(item["type_code"], {})

        submittal = {
            "id": sub_id,
            "number": sub_number,
            "spec_section": item.get("spec_section", ""),
            "division": div,
            "division_name": item.get("division_name", ""),
            "trade": item.get("trade", "TBD"),
            "description": item["description"],
            "type_code": item["type_code"],
            "type_name": type_info.get("name", ""),
            "status": "Not Started",
            "lead_time_weeks": item.get("lead_time_weeks", 4),
            "date_required": "",
            "date_submitted": "",
            "date_returned": "",
            "disposition": "",
            "resubmittal_count": 0,
            "notes": f"Imported from spec scan: {scan.get('source_file', '')}",
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
        }
        register["submittals"].append(submittal)
        register["metadata"]["next_id"] = sub_id + 1
        count += 1

    save_register(register)
    print(f"Imported {count} submittals from scan results.")


def cmd_add(args):
    """Add a single submittal to the register."""
    register = load_register()
    csi = load_csi_data()

    div = args.div.zfill(2)
    type_code = args.type.upper()

    if type_code not in csi["submittal_types"]:
        print(f"Error: Unknown type code '{type_code}'.")
        print(f"Valid types: {', '.join(csi['submittal_types'].keys())}")
        sys.exit(1)

    div_info = csi["divisions"].get(div, {})
    type_info = csi["submittal_types"][type_code]

    sub_id = register["metadata"]["next_id"]
    sub_number = next_submittal_number(register, div)

    submittal = {
        "id": sub_id,
        "number": sub_number,
        "spec_section": args.spec or f"{div} 00 00",
        "division": div,
        "division_name": div_info.get("name", f"Division {div}"),
        "trade": args.trade or div_info.get("trade", "TBD"),
        "description": args.desc,
        "type_code": type_code,
        "type_name": type_info["name"],
        "status": "Not Started",
        "lead_time_weeks": int(args.lead) if args.lead else 4,
        "date_required": "",
        "date_submitted": "",
        "date_returned": "",
        "disposition": "",
        "resubmittal_count": 0,
        "notes": "",
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
    }

    register["submittals"].append(submittal)
    register["metadata"]["next_id"] = sub_id + 1
    save_register(register)
    print(f"Added submittal {sub_number}: {args.desc}")


def cmd_list(args):
    """List submittals with optional filters."""
    register = load_register()
    submittals = register["submittals"]

    # Apply filters
    if args.status:
        submittals = [s for s in submittals if s["status"].lower() == args.status.lower()]
    if args.division:
        div = args.division.zfill(2)
        submittals = [s for s in submittals if s["division"] == div]
    if args.trade:
        submittals = [s for s in submittals if args.trade.lower() in s["trade"].lower()]
    if args.critical:
        submittals = [s for s in submittals if s["lead_time_weeks"] >= 8 and s["status"] in ("Not Started", "In Preparation")]

    if not submittals:
        print("No submittals match the filter criteria.")
        return

    print(f"\n{'#':<10} {'Stat':<5} {'Div':<5} {'Type':<5} {'Lead':<6} {'Trade':<25} {'Description':<40}")
    print(f"{'-'*10} {'-'*5} {'-'*5} {'-'*5} {'-'*6} {'-'*25} {'-'*40}")

    for s in submittals:
        sym = STATUS_SYMBOLS.get(s["status"], "[ ]")
        lead_str = f"{s['lead_time_weeks']}wk"
        print(f"{s['number']:<10} {sym:<5} {s['division']:<5} {s['type_code']:<5} {lead_str:<6} {s['trade'][:25]:<25} {s['description'][:40]}")

    print(f"\n  Total: {len(submittals)} submittals")


def cmd_update(args):
    """Update a submittal's status, lead time, dates, or notes."""
    register = load_register()

    target = None
    for s in register["submittals"]:
        if s["number"] == args.submittal_id or str(s["id"]) == args.submittal_id:
            target = s
            break

    if not target:
        print(f"Error: Submittal '{args.submittal_id}' not found.")
        sys.exit(1)

    changes = []

    if args.status:
        # Validate status
        match = None
        for valid in VALID_STATUSES:
            if args.status.lower() == valid.lower():
                match = valid
                break
        if not match:
            print(f"Error: Invalid status '{args.status}'.")
            print(f"Valid statuses: {', '.join(VALID_STATUSES)}")
            sys.exit(1)

        old_status = target["status"]
        target["status"] = match
        target["disposition"] = match
        changes.append(f"Status: {old_status} -> {match}")

        # Auto-increment resubmittal count on R&R
        if match == "Revise & Resubmit":
            target["resubmittal_count"] += 1
            changes.append(f"Resubmittal #{target['resubmittal_count']}")

    if args.lead:
        old_lead = target["lead_time_weeks"]
        target["lead_time_weeks"] = int(args.lead)
        changes.append(f"Lead time: {old_lead}wk -> {args.lead}wk")

    if args.date_submitted:
        target["date_submitted"] = args.date_submitted
        changes.append(f"Date submitted: {args.date_submitted}")

    if args.date_returned:
        target["date_returned"] = args.date_returned
        changes.append(f"Date returned: {args.date_returned}")

    if args.notes:
        target["notes"] = args.notes
        changes.append("Notes updated")

    target["updated"] = datetime.now().isoformat()
    save_register(register)

    print(f"Updated {target['number']}: {target['description']}")
    for c in changes:
        print(f"  {c}")


def cmd_dashboard(args):
    """Display a summary dashboard of submittal status."""
    register = load_register()
    submittals = register["submittals"]
    project = register["project"]

    if not submittals:
        print("No submittals in register.")
        return

    print(f"\n{'=' * 72}")
    print(f"  SUBMITTAL DASHBOARD — {project['name']}")
    if project.get("contract_number"):
        print(f"  Contract: {project['contract_number']}")
    print(f"  As of: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 72}")

    # Status summary
    status_counts = {}
    for s in submittals:
        status_counts[s["status"]] = status_counts.get(s["status"], 0) + 1

    print(f"\n  STATUS SUMMARY")
    print(f"  {'-' * 40}")
    for status in VALID_STATUSES:
        count = status_counts.get(status, 0)
        if count > 0:
            bar = "#" * min(count, 30)
            sym = STATUS_SYMBOLS.get(status, "[ ]")
            print(f"  {sym} {status:<22} {count:>4}  {bar}")
    print(f"  {'':>27} {'----':>4}")
    print(f"  {'TOTAL':>27} {len(submittals):>4}")

    # Division breakdown
    print(f"\n  BY DIVISION")
    print(f"  {'-' * 40}")
    div_counts = {}
    for s in submittals:
        key = f"{s['division']} - {s['division_name']}"
        div_counts[key] = div_counts.get(key, 0) + 1
    for div_key in sorted(div_counts.keys()):
        print(f"  {div_key:<35} {div_counts[div_key]:>4}")

    # Critical path items (long lead, not yet approved)
    critical = [
        s for s in submittals
        if s["lead_time_weeks"] >= 8
        and s["status"] in ("Not Started", "In Preparation", "Submitted", "Under Review", "Revise & Resubmit")
    ]
    if critical:
        critical.sort(key=lambda x: -x["lead_time_weeks"])
        print(f"\n  CRITICAL PATH ITEMS (lead >= 8 weeks, not yet approved)")
        print(f"  {'-' * 60}")
        print(f"  {'#':<10} {'Lead':<6} {'Status':<20} {'Description':<35}")
        for s in critical[:15]:
            sym = STATUS_SYMBOLS.get(s["status"], "[ ]")
            print(f"  {s['number']:<10} {s['lead_time_weeks']}wk{'':>3} {sym} {s['status']:<16} {s['description'][:35]}")

    # Overdue / action needed
    action_needed = [s for s in submittals if s["status"] == "Revise & Resubmit"]
    if action_needed:
        print(f"\n  ACTION REQUIRED — Revise & Resubmit ({len(action_needed)})")
        print(f"  {'-' * 60}")
        for s in action_needed:
            print(f"  {s['number']:<10} {s['trade']:<25} {s['description'][:35]}")

    print()


def cmd_report(args):
    """Generate a formatted report."""
    register = load_register()
    submittals = register["submittals"]
    project = register["project"]
    fmt = args.format or "text"

    if fmt == "csv":
        csv_path = Path.cwd() / REGISTER_CSV
        export_csv(register)
        print(f"CSV exported to: {csv_path}")
        return

    if fmt == "text":
        print(f"\nSUBMITTAL REGISTER REPORT")
        print(f"{'=' * 72}")
        print(f"Project:  {project['name']}")
        print(f"Contract: {project.get('contract_number', 'N/A')}")
        print(f"Date:     {datetime.now().strftime('%Y-%m-%d')}")
        print(f"Total:    {len(submittals)} submittals")
        print(f"{'=' * 72}")

        # Group by division
        divisions = {}
        for s in submittals:
            key = s["division"]
            if key not in divisions:
                divisions[key] = []
            divisions[key].append(s)

        for div_code in sorted(divisions.keys()):
            items = divisions[div_code]
            div_name = items[0]["division_name"]
            trade = items[0]["trade"]

            print(f"\n  Division {div_code} — {div_name}")
            print(f"  Trade: {trade}")
            print(f"  {'#':<10} {'Type':<5} {'Status':<22} {'Lead':<6} {'Description'}")
            print(f"  {'-'*10} {'-'*5} {'-'*22} {'-'*6} {'-'*30}")

            for s in items:
                sym = STATUS_SYMBOLS.get(s["status"], "[ ]")
                lead_str = f"{s['lead_time_weeks']}wk"
                print(f"  {s['number']:<10} {s['type_code']:<5} {sym} {s['status']:<18} {lead_str:<6} {s['description'][:40]}")

        # Summary statistics
        approved = len([s for s in submittals if s["status"] in ("Approved", "Approved as Noted", "For Record Only", "Closed")])
        pending = len([s for s in submittals if s["status"] in ("Not Started", "In Preparation")])
        in_review = len([s for s in submittals if s["status"] in ("Submitted", "Under Review")])
        action = len([s for s in submittals if s["status"] in ("Revise & Resubmit", "Rejected")])

        print(f"\n{'=' * 72}")
        print(f"  SUMMARY")
        print(f"  Approved/Closed:     {approved:>4}  ({approved/len(submittals)*100:.0f}%)" if submittals else "")
        print(f"  In Review:           {in_review:>4}  ({in_review/len(submittals)*100:.0f}%)" if submittals else "")
        print(f"  Pending:             {pending:>4}  ({pending/len(submittals)*100:.0f}%)" if submittals else "")
        print(f"  Action Required:     {action:>4}  ({action/len(submittals)*100:.0f}%)" if submittals else "")
        print()


# ─── Main ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Construction Submittal Tracker for JOC & Public Works",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init
    p_init = subparsers.add_parser("init", help="Initialize a new submittal register")
    p_init.add_argument("project_name", help="Project name")
    p_init.add_argument("--contract-no", help="Contract number")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing register")

    # generate
    p_gen = subparsers.add_parser("generate", help="Generate submittals from CSI reference data")
    p_gen.add_argument("--divisions", help="Comma-separated division codes (e.g., 03,05,26)")

    # scan
    p_scan = subparsers.add_parser("scan", help="Scan a spec file for submittal requirements")
    p_scan.add_argument("spec_file", help="Path to specification file (text/PDF)")

    # import-spec
    p_import = subparsers.add_parser("import-spec", help="Import scan results into register")
    p_import.add_argument("scan_output", help="Path to scan results JSON")

    # add
    p_add = subparsers.add_parser("add", help="Add a submittal manually")
    p_add.add_argument("--desc", required=True, help="Submittal description")
    p_add.add_argument("--div", required=True, help="CSI division code (e.g., 03, 26)")
    p_add.add_argument("--type", required=True, help="Type code (SD, PD, SS, CP, DI, MO, QC, CL, WP, SR)")
    p_add.add_argument("--spec", help="Spec section (e.g., 03 30 00)")
    p_add.add_argument("--trade", help="Responsible trade")
    p_add.add_argument("--lead", help="Lead time in weeks")

    # list
    p_list = subparsers.add_parser("list", help="List submittals with optional filters")
    p_list.add_argument("--status", help="Filter by status")
    p_list.add_argument("--division", help="Filter by division code")
    p_list.add_argument("--trade", help="Filter by trade name (partial match)")
    p_list.add_argument("--critical", action="store_true", help="Show only critical path items (lead >= 8wk, not approved)")

    # update
    p_update = subparsers.add_parser("update", help="Update a submittal")
    p_update.add_argument("submittal_id", help="Submittal number (e.g., 05-001) or ID")
    p_update.add_argument("--status", help="New status")
    p_update.add_argument("--lead", help="New lead time in weeks")
    p_update.add_argument("--notes", help="Notes")
    p_update.add_argument("--date-submitted", help="Date submitted (YYYY-MM-DD)")
    p_update.add_argument("--date-returned", help="Date returned (YYYY-MM-DD)")

    # dashboard
    subparsers.add_parser("dashboard", help="Display status dashboard")

    # report
    p_report = subparsers.add_parser("report", help="Generate a report")
    p_report.add_argument("--format", choices=["text", "csv"], default="text", help="Output format")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "init": cmd_init,
        "generate": cmd_generate,
        "scan": cmd_scan,
        "import-spec": cmd_import_spec,
        "add": cmd_add,
        "list": cmd_list,
        "update": cmd_update,
        "dashboard": cmd_dashboard,
        "report": cmd_report,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
