#!/usr/bin/env python3
"""
deploy_atlas.py — automatic, idempotent Plans Atlas deployment orchestrator.

Invoked when a bid/project is confirmed (initial knowledge-base creation or
review) and again whenever the drawing set changes. It rebuilds the NTXP Plans
Atlas only when needed and otherwise exits cleanly saying "up to date".

Sequence (each step is a sibling script run via subprocess):

    1. build_atlas_data.py   drawing PDFs -> model/sections/plans_atlas.json (+ words, images)
    2. assemble_model.py     re-assemble so canonical-model.json carries plans_atlas
    3. build_atlas_html.py   canonical model -> <Construction Documents>/Plans Atlas/plans-atlas.html
    4. README.txt            plain-language note beside the deliverable

Idempotency: a SHA-256 manifest of the discovered drawing PDFs is kept in
<project>/model/.atlas-state.json. Same manifest + outputs present = up to date.

Source PDFs are only ever read, never modified or moved. Python 3.11, stdlib only.
Logs go to stderr with a [deploy-atlas] prefix; the machine-readable result is
the final JSON on stdout.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
STATE_NAME = ".atlas-state.json"
OUT_SUBDIR = "Plans Atlas"
OUT_HTML = "plans-atlas.html"
CONST_DOC_NAMES = {"construction documents", "const docs", "const. docs",
                   "construction docs", "plans", "drawings"}
README_TEXT = (
    "This is the NTXP Plans Atlas: the whole drawing set as one linked, searchable viewer.\n"
    "It is fully offline - open plans-atlas.html in any browser; nothing to install, no connection needed.\n"
    "It regenerates automatically whenever the drawings change, so never edit it by hand.\n"
)


def log(msg):
    print(f"[deploy-atlas] {msg}", file=sys.stderr)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2) + "\n")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "project"


def norm_dirname(name):
    return re.sub(r"^[\d\W_]+", "", name).strip().lower()


def find_const_docs(project, create=True):
    """BFS (depth <= 3) for a Construction Documents-style folder."""
    queue = deque([(project, 0)])
    while queue:
        cur, depth = queue.popleft()
        try:
            kids = sorted(p for p in cur.iterdir() if p.is_dir())
        except OSError:
            continue
        for kid in kids:
            if norm_dirname(kid.name) in CONST_DOC_NAMES:
                return kid, False
            if depth + 1 < 3 and kid.name != "model":
                queue.append((kid, depth + 1))
    return project / "Construction Documents", True


def discover_pdfs(pdf_dir):
    out = []
    for p in sorted(pdf_dir.glob("**/*.pdf")) + sorted(pdf_dir.glob("**/*.PDF")):
        rel_parts = p.relative_to(pdf_dir).parts
        if OUT_SUBDIR in rel_parts[:-1] or p.name.lower().startswith("plans-atlas"):
            continue
        if p not in out:
            out.append(p)
    return sorted(out)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(pdfs, base):
    manifest = {}
    for p in pdfs:
        st = p.stat()
        manifest[p.relative_to(base).as_posix()] = {
            "sha256": sha256_file(p), "bytes": st.st_size, "mtime": int(st.st_mtime)}
    return manifest


def manifest_key(manifest):
    """Compare on content only (mtime changes alone do not force a rebuild)."""
    return {k: v["sha256"] for k, v in (manifest or {}).items()}


def run_step(label, cmd):
    log(f"{label}: {' '.join(str(c) for c in cmd[1:])}")
    proc = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if proc.stderr:
        sys.stderr.write(proc.stderr if proc.stderr.endswith("\n") else proc.stderr + "\n")
    return proc


def sheet_count(model_dir):
    sec = load_json(model_dir / "sections" / "plans_atlas.json") or {}
    return len(sec.get("sheets") or [])


def write_minimal_model(model_dir, project, dossier):
    title = project.name.replace("_", " ").replace("-", " ").strip() or "Project"
    model = {"schema_version": "1.0",
             "project": {"title": title, "slug": slugify(project.name)},
             "sections": {"plans_atlas": "sections/plans_atlas.json"},
             "source": {"dossier_dir": str(dossier)}}
    write_json(model_dir / "canonical-model.json", model)
    log("canonical-model.json not present - wrote a minimal one so the viewer can render")


def plan_for(args, project, const_docs, created, pdf_dir, pdfs, manifest, state, state_path):
    stored = (state or {}).get("pdf_manifest")
    outs = [project / o for o in (state or {}).get("outputs", [])]
    outputs_ok = bool(outs) and all(o.exists() for o in outs)
    unchanged = state is not None and manifest_key(stored) == manifest_key(manifest)
    if not pdfs:
        action = "no_drawings"
    elif unchanged and outputs_ok and not args.force:
        action = "up_to_date"
    else:
        action = "rebuild"
    reason = ("forced" if args.force else
              "no previous state" if state is None else
              "drawing set changed" if not unchanged else
              "outputs missing" if not outputs_ok else "no drawing changes")
    return {"action": action, "reason": reason, "project": str(project),
            "const_docs": str(const_docs), "const_docs_will_be_created": created,
            "pdf_dir": str(pdf_dir), "sheets_found": len(pdfs),
            "atlas": str(const_docs / OUT_SUBDIR / OUT_HTML),
            "state_file": str(state_path), "event": args.event,
            "atlas_version": (state or {}).get("atlas_version", 0)}


def main():
    ap = argparse.ArgumentParser(description="Idempotently deploy the NTXP Plans Atlas for a project.")
    ap.add_argument("--project", required=True, help="Project root directory.")
    ap.add_argument("--dossier", help="Dossier dir for assemble_model.py (default: --project).")
    ap.add_argument("--const-docs", help="Construction Documents folder (default: auto-detect/create).")
    ap.add_argument("--pdf-dir", help="Drawing PDF folder (default: the const-docs folder).")
    ap.add_argument("--company", default="NTXP")
    ap.add_argument("--force", action="store_true", help="Rebuild regardless of state.")
    ap.add_argument("--check", action="store_true", help="Report would-rebuild/up-to-date as JSON; no changes.")
    ap.add_argument("--dry-run", action="store_true", help="Print the plan JSON; change nothing.")
    ap.add_argument("--event", default="manual",
                    help="Reason recorded in state (bid_confirmed, project_confirmed, kb_initial_review, addendum, manual).")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    if not project.is_dir():
        log(f"project directory not found: {project}")
        sys.exit(2)
    dossier = Path(args.dossier).resolve() if args.dossier else project
    model_dir = project / "model"
    state_path = model_dir / STATE_NAME

    if args.const_docs:
        const_docs, created = Path(args.const_docs).resolve(), False
        created = not const_docs.exists()
    else:
        const_docs, created = find_const_docs(project)
    pdf_dir = Path(args.pdf_dir).resolve() if args.pdf_dir else const_docs

    pdfs = discover_pdfs(pdf_dir) if pdf_dir.is_dir() else []
    manifest = build_manifest(pdfs, pdf_dir)
    state = load_json(state_path)
    plan = plan_for(args, project, const_docs, created, pdf_dir, pdfs, manifest, state, state_path)

    if args.dry_run or args.check:
        plan["mode"] = "dry_run" if args.dry_run else "check"
        plan["would_rebuild"] = plan["action"] == "rebuild"
        print(json.dumps(plan, indent=2))
        return

    atlas_path = const_docs / OUT_SUBDIR / OUT_HTML
    version = (state or {}).get("atlas_version", 0)

    if plan["action"] == "no_drawings":
        log(f"No drawing PDFs found under {pdf_dir} yet - the atlas will build on the next sync that brings plans.")
        write_json(state_path, {"schema": 1, "last_built": (state or {}).get("last_built"),
                                "event": args.event, "pdf_manifest": {}, "outputs": [],
                                "atlas_version": version})
        print(json.dumps({"status": "no_drawings", "atlas": None, "sheets": 0,
                          "event": args.event, "atlas_version": version,
                          "note": f"No drawing PDFs found under {pdf_dir} yet - the atlas will build on the next sync that brings plans."},
                         indent=2))
        return

    if plan["action"] == "up_to_date":
        n = sheet_count(model_dir)
        log(f"Plans Atlas up to date ({n} sheets, no drawing changes)")
        print(json.dumps({"status": "up_to_date", "atlas": str(atlas_path), "sheets": n,
                          "event": args.event, "atlas_version": version}, indent=2))
        return

    # ---- rebuild -----------------------------------------------------------
    log(f"rebuilding ({plan['reason']}; event={args.event}; {len(pdfs)} PDFs)")
    if created:
        log(f"created Construction Documents folder: {const_docs}")
    const_docs.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    model_json = model_dir / "canonical-model.json"

    cmd = [py, SCRIPTS_DIR / "build_atlas_data.py", "--dir", pdf_dir, "--out", model_dir]
    if model_json.exists():
        cmd += ["--model", model_dir]
    proc = run_step("step 1/4 extract drawings", cmd)
    if proc.returncode != 0:
        log(f"FAILED: build_atlas_data.py exited {proc.returncode}; atlas not deployed.")
        sys.exit(proc.returncode or 1)

    section_path = model_dir / "sections" / "plans_atlas.json"
    section = load_json(section_path) or {}
    pack_qa = (section.get("source_set") or {}).get("pack_qa")
    if pack_qa == "blocked":
        log("WARNING: pack_qa is 'blocked' - review the drawing pack inventory; continuing so the state is visible.")

    other_sections = [p for p in (model_dir / "sections").glob("*.json") if p.name != "plans_atlas.json"]
    if model_json.exists() or other_sections:
        proc = run_step("step 2/4 assemble model", [py, SCRIPTS_DIR / "assemble_model.py",
                        "--dossier", dossier, "--generated-at", now_iso()])
        if proc.returncode != 0:
            if section_path.exists():
                log(f"WARNING: assemble_model.py exited {proc.returncode}; continuing with the atlas section.")
            else:
                log("FAILED: assemble_model.py failed and no atlas section exists.")
                sys.exit(proc.returncode or 1)
    else:
        log("step 2/4 assemble model: skipped (dossier not assembled yet)")
    if not model_json.exists():
        write_minimal_model(model_dir, project, dossier)

    out_dir = const_docs / OUT_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = run_step("step 3/4 render viewer", [py, SCRIPTS_DIR / "build_atlas_html.py",
                    "--model", model_json, "--out", atlas_path, "--company", args.company])
    if proc.returncode != 0 or not atlas_path.exists():
        log(f"FAILED: build_atlas_html.py exited {proc.returncode}; atlas not deployed.")
        sys.exit(proc.returncode or 1)

    outputs = [atlas_path]
    if "atlas/img/" in atlas_path.read_text(errors="replace"):
        import shutil
        words = model_dir / "atlas-words.json"
        if words.exists():
            shutil.copy2(words, out_dir / words.name)
            outputs.append(out_dir / words.name)
        img = model_dir / "atlas" / "img"
        if img.is_dir():
            shutil.copytree(img, out_dir / "atlas" / "img", dirs_exist_ok=True)
            log("copied atlas/img and atlas-words.json beside the html (relative references found)")

    readme = out_dir / "README.txt"
    readme.write_text(README_TEXT)
    outputs.append(readme)
    log("step 4/4 wrote README.txt")

    version += 1
    n = sheet_count(model_dir)
    rel_outputs = []
    for o in outputs + [section_path]:
        if o.exists():
            rel_outputs.append(o.relative_to(project).as_posix() if project in o.parents else str(o))
    write_json(state_path, {"schema": 1, "last_built": now_iso(), "event": args.event,
                            "pdf_manifest": manifest, "outputs": rel_outputs, "atlas_version": version})
    log(f"Plans Atlas built: {atlas_path} ({n} sheets, version {version})")
    print(json.dumps({"status": "built", "atlas": str(atlas_path), "sheets": n,
                      "event": args.event, "atlas_version": version}, indent=2))


if __name__ == "__main__":
    main()
