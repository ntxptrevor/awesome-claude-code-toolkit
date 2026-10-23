#!/usr/bin/env python3
"""Interlink the Phase 1 project Knowledge Base with the Plans Atlas.

Deterministic, stdlib only, no network. Reads a Phase 1 KB directory (kb.json,
kb_index.jsonl, curation.json, extracts/) and a plans_atlas.json section, and
writes two files:

  interlinks.json     sheet <-> KB facts, division <-> sheets <-> KB, spec section
                      <-> sheets <-> KB, a back-reference map keyed by KB chunk id,
                      and everything that did not match (never resolved, only listed)
  atlas-chunks.json   records the KB index folds in as domains atlas_sheet,
                      atlas_division and atlas_spec, so `kb.py search` finds the
                      drawings and every fact points back to its sheet

Join keys, strongest first (each link records `via` and `confidence`):
  sheet_number   normalized sheet number equal                         0.95
  sheet_field    a KB record's own `sheet` field names the sheet        0.90
  trade_sheets   curation trade lists the sheet                         0.85
  spec_section   KB spec section is cited on the sheet in the atlas     0.80
  doc_page       same source document and page                          0.70
  text_mention   a real atlas sheet number appears in the record text   0.60
  division       same CSI division, capped at six sheets                0.40

KB extracts are never edited; this is an overlay. Called by phase1_receiver.py.
"""
import argparse
import hashlib
import json
import re
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

SCHEMA = "ntxp.interlinks/1"
SHEET_TOKEN = re.compile(r"\b[A-Z]{1,3}[-.]?\d{1,3}(?:\.\d{1,2})?[A-Z]?\b")
SPEC_TOKEN = re.compile(r"\b\d{2}[\s.-]?\d{2}[\s.-]?\d{2}\b")
ROLE_OF = {"sheet_note": "notes", "schedule_row": "schedules", "submittal": "submittals",
           "product": "products", "requirement": "requirements", "scope_item": "scope",
           "trade": "trades", "general_scope": "other", "phase2_flag": "other"}
CONF = {"sheet_number": 0.95, "sheet_field": 0.90, "trade_sheets": 0.85, "spec_section": 0.80,
        "doc_page": 0.70, "text_mention": 0.60, "division": 0.40}
DIVISION_CAP = 6


def nk(value):
    """Normalized key: A-101, a101 and A1.01 all become A101."""
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def spec_key(value):
    d = re.sub(r"\D", "", str(value or ""))
    return d[:6] if len(d) >= 6 else d


def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def load_jsonl(path):
    rows = []
    try:
        for line in Path(path).read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    except (OSError, ValueError):
        pass
    return rows


def sheet_refs(text_or_list):
    """Split a field such as 'A-101, A-102 / A-103' into normalized sheet keys."""
    if isinstance(text_or_list, (list, tuple)):
        parts = [str(x) for x in text_or_list]
    else:
        parts = re.split(r"[,;/&]|\band\b|\bthru\b", str(text_or_list or ""), flags=re.I)
    out = []
    for p in parts:
        k = nk(p)
        if k and re.match(r"^[A-Z]{1,3}\d", k):
            out.append(k)
    return out


def title_words(t):
    return {w for w in re.findall(r"[a-z0-9]+", str(t or "").lower()) if len(w) > 2}


def kb_chunks(kb_dir, slug):
    """Chunks from kb_index.jsonl; if the index is missing, derive reference-only chunks."""
    rows = [r for r in load_jsonl(Path(kb_dir) / "kb_index.jsonl")
            if not str(r.get("domain", "")).startswith("atlas_")]
    if rows:
        return rows, False
    ex = Path(kb_dir) / "extracts"
    derived = []
    for domain, fname in (("scope_item", "scope-items"), ("product", "products"), ("requirement", "requirements"),
                          ("sheet_note", "sheet-notes"), ("submittal", "submittals")):
        for i, rec in enumerate(load_json(ex / f"{fname}.json", []) or []):
            derived.append({"id": f"{slug}:{domain}:noindex{i}", "domain": domain, "record": rec,
                            "text": rec.get("text") or rec.get("item") or "", "doc": rec.get("_doc"),
                            "csi_division": rec.get("csi_division")})
    kb = load_json(Path(kb_dir) / "kb.json", {}) or {}
    for i, sh in enumerate(kb.get("sheet_index") or []):
        derived.append({"id": f"{slug}:sheet:noindex{i}", "domain": "sheet", "record": sh,
                        "text": f"{sh.get('sheet_number')} {sh.get('sheet_title')}", "doc": sh.get("_doc"),
                        "page_ref": sh.get("page_index"), "csi_division": None})
    return derived, True


def build(kb_dir, atlas, viewer_rel="Plans Atlas/plans-atlas.html", request_id="", ignition_dir=None):
    kb_dir = Path(kb_dir)
    kb = load_json(kb_dir / "kb.json", {}) or {}
    slug = (kb.get("project") or {}).get("slug") or kb_dir.name
    curation = load_json(kb_dir / "curation.json", {}) or {}
    chunks, index_missing = kb_chunks(kb_dir, slug)

    sheets = atlas.get("sheets") or []
    by_key = {}
    for s in sheets:
        by_key.setdefault(nk(s.get("sheet_no") or s.get("sheet_id")), s)
    spec_sheets = {}
    for sp in (atlas.get("concepts") or {}).get("specs") or []:
        spec_sheets[spec_key(sp.get("section"))] = (sp, list(sp.get("sheet_ids") or []))
    trade_sheets = {}
    for t in (atlas.get("concepts") or {}).get("trades") or []:
        trade_sheets[str(t.get("division"))] = (t, list(t.get("sheet_ids") or []))
    sheet_by_id = {s["sheet_id"]: s for s in sheets}

    doc_stem = lambda d: nk(Path(str(d or "")).stem)          # noqa: E731
    atlas_by_docpage = {}
    for s in sheets:
        atlas_by_docpage[(doc_stem(s.get("source_doc")), int(s.get("page") or 0))] = s

    links = {s["sheet_id"]: {"notes": [], "schedules": [], "submittals": [], "products": [],
                             "requirements": [], "scope": [], "trades": [], "other": []} for s in sheets}
    via_log = {}          # (sheet_id, chunk_id) -> (via, confidence)
    backrefs = {}

    def attach(chunk, sheet_id, via):
        cid = chunk["id"]
        key = (sheet_id, cid)
        conf = CONF[via]
        if key in via_log and via_log[key][1] >= conf:
            return
        via_log[key] = (via, conf)
        role = ROLE_OF.get(chunk.get("domain"), "other")
        if cid not in links[sheet_id][role]:
            links[sheet_id][role].append(cid)
        refs = backrefs.setdefault(cid, [])
        refs[:] = [r for r in refs if r["sheet_id"] != sheet_id]
        refs.append({"sheet_id": sheet_id, "via": via, "confidence": conf})

    # 1. sheet-to-sheet: KB sheet index <-> atlas sheet
    kb_sheet_chunk, title_conflicts = {}, []
    matched_kb_sheets = set()
    for c in chunks:
        if c.get("domain") != "sheet":
            continue
        rec = c.get("record") or {}
        s, via = by_key.get(nk(rec.get("sheet_number"))), "sheet_number"
        if s is None:
            try:
                page = int(rec.get("page_index")) + 1
            except (TypeError, ValueError):
                page = 0
            s, via = atlas_by_docpage.get((doc_stem(rec.get("_doc") or c.get("doc")), page)), "doc_page"
        if s is None:
            continue
        sid = s["sheet_id"]
        kb_sheet_chunk[sid] = {"chunk": c["id"], "via": via, "confidence": CONF[via],
                               "kb_sheet_number": rec.get("sheet_number"), "kb_title": rec.get("sheet_title")}
        matched_kb_sheets.add(c["id"])
        if via == "sheet_number":
            kw, aw = title_words(rec.get("sheet_title")), title_words(s.get("title"))
            if kw and aw and len(kw & aw) / len(kw | aw) < 0.34:
                title_conflicts.append({"sheet_id": sid, "sheet_no": s.get("sheet_no"),
                                        "kb_title": rec.get("sheet_title"), "atlas_title": s.get("title")})
    # 2. every other KB chunk -> sheets
    for c in chunks:
        dom = c.get("domain")
        if dom in ("sheet", "contact", "date", "lesson", "pricing"):
            continue
        rec = c.get("record") or {}
        text = " ".join(str(x) for x in (c.get("text"), rec.get("text"), rec.get("item")) if x)
        hit = False
        for k in sheet_refs(rec.get("sheet")):
            if k in by_key:
                attach(c, by_key[k]["sheet_id"], "sheet_field")
                hit = True
        if dom == "trade":
            for k in sheet_refs(rec.get("sheets")):
                if k in by_key:
                    attach(c, by_key[k]["sheet_id"], "trade_sheets")
                    hit = True
            for sp in rec.get("spec_sections") or []:
                for sid in spec_sheets.get(spec_key(sp), (None, []))[1]:
                    attach(c, sid, "spec_section")
                    hit = True
        sp_keys = {spec_key(rec.get("spec_section"))} | {spec_key(m) for m in SPEC_TOKEN.findall(text)}
        for k in sp_keys:
            for sid in spec_sheets.get(k, (None, []))[1]:
                attach(c, sid, "spec_section")
                hit = True
        for tok in SHEET_TOKEN.findall(text.upper()):
            k = nk(tok)
            if len(k) >= 3 and k in by_key:
                attach(c, by_key[k]["sheet_id"], "text_mention")
                hit = True
        if not hit and dom in ("submittal", "product", "scope_item", "requirement"):
            div = str(c.get("csi_division") or rec.get("csi_division") or "")[:2]
            for sid in (trade_sheets.get(div, (None, []))[1])[:DIVISION_CAP]:
                attach(c, sid, "division")

    # 3. divisions and specs
    divisions, specs = {}, {}
    kb_by_div = {}
    for c in chunks:
        d = str(c.get("csi_division") or (c.get("record") or {}).get("csi_division") or "")[:2]
        if d:
            kb_by_div.setdefault(d, {}).setdefault(c.get("domain"), []).append(c["id"])
    div_files = {}
    for f in (kb_dir / "knowledge-base" / "Divisions").glob("*") if (kb_dir / "knowledge-base" / "Divisions").is_dir() else []:
        m = re.match(r"(\d{2})", f.name)
        if m:
            div_files[m.group(1)] = f.relative_to(kb_dir).as_posix()
    labels = {t.get("division"): t.get("label") for t in (atlas.get("concepts") or {}).get("trades") or []}
    for d in sorted(set(kb_by_div) | set(trade_sheets)):
        t = trade_sheets.get(d, ({}, []))
        divisions[d] = {"label": labels.get(d) or "", "atlas_sheets": t[1],
                        "specs": list(t[0].get("spec_sections") or []) if t[0] else [],
                        "kb_counts": {k: len(v) for k, v in sorted(kb_by_div.get(d, {}).items())},
                        "kb_division_file": div_files.get(d),
                        "itb_package": ("ignition/itb/itb-packages.html" if ignition_dir and (Path(ignition_dir) / "itb" / "itb-packages.html").exists() else None)}
    for key, (sp, sids) in spec_sheets.items():
        kb_ids = sorted({cid for sid in sids for role in links[sid].values() for cid in role
                         if any(r["via"] == "spec_section" and r["sheet_id"] == sid for r in backrefs.get(cid, []))})
        specs[sp.get("section")] = {"title": sp.get("title") or "", "division": sp.get("division"),
                                    "atlas_sheets": sids, "kb_chunks": kb_ids[:50]}

    def anchor(sid):
        return f"{viewer_rel}#sheet={quote(sid, safe='')}"

    out_sheets = {}
    for s in sheets:
        sid = s["sheet_id"]
        out_sheets[sid] = {"sheet_no": s.get("sheet_no"), "title": s.get("title"), "page": s.get("page"),
                           "source_doc": s.get("source_doc"), "divisions": list(s.get("divisions") or []),
                           "viewer": anchor(sid), "kb_sheet": kb_sheet_chunk.get(sid),
                           "links": {k: v for k, v in links[sid].items() if v},
                           "link_counts": {k: len(v) for k, v in links[sid].items() if v}}
    unmatched_atlas = [sid for sid in links if sid not in kb_sheet_chunk]
    unmatched_kb = []
    for c in chunks:
        if c.get("domain") == "sheet" and c["id"] not in matched_kb_sheets:
            rec = c.get("record") or {}
            unmatched_kb.append({"chunk": c["id"], "sheet_number": rec.get("sheet_number"),
                                 "sheet_title": rec.get("sheet_title"), "doc": rec.get("_doc")})
    stats = {"atlas_sheets": len(sheets), "kb_sheets_matched": len(kb_sheet_chunk),
             "kb_chunks_linked": len(backrefs), "links": len(via_log),
             "title_conflicts": len(title_conflicts), "atlas_sheets_without_kb": len(unmatched_atlas),
             "kb_sheets_without_atlas": len(unmatched_kb), "kb_index_missing": index_missing}
    review = []
    if unmatched_kb:
        review.append(f"{len(unmatched_kb)} sheet(s) in the KB sheet index were not found in the drawing PDFs "
                      f"(e.g. {', '.join(str(u['sheet_number']) for u in unmatched_kb[:5])}): the set may be incomplete.")
    if title_conflicts:
        review.append(f"{len(title_conflicts)} sheet title(s) differ between the KB and the atlas; both are kept.")
    if index_missing:
        review.append("kb_index.jsonl was missing, so links point at provisional ids; rebuild the index and re-run.")
    interlinks = {"schema": SCHEMA, "request_id": request_id, "kb_slug": slug, "viewer": viewer_rel,
                  "stats": stats, "sheets": out_sheets, "divisions": divisions, "specs": specs,
                  "chunk_backrefs": backrefs,
                  "unmatched": {"atlas_sheets": unmatched_atlas, "kb_sheets": unmatched_kb},
                  "title_conflicts": title_conflicts, "needs_review": review}

    # 4. chunk records for the KB index
    recs = []
    for s in sheets:
        sid = s["sheet_id"]
        sh = out_sheets[sid]
        recs.append({"_kind": "sheet", "sheet_id": sid, "sheet_no": s.get("sheet_no"), "title": s.get("title"),
                     "discipline": s.get("discipline"), "divisions": sh["divisions"],
                     "csi_division": (sh["divisions"] or [None])[0], "doc": s.get("source_doc"),
                     "page_index": str(max(int(s.get("page") or 1) - 1, 0)), "viewer": sh["viewer"],
                     "kb_sheet_chunk": (sh["kb_sheet"] or {}).get("chunk"), "kb_links": sh["links"],
                     "kb_title": (sh["kb_sheet"] or {}).get("kb_title")})
    for d, v in divisions.items():
        recs.append({"_kind": "division", "division": d, "csi_division": d, "label": v["label"],
                     "atlas_sheets": v["atlas_sheets"], "specs": v["specs"], "kb_counts": v["kb_counts"],
                     "kb_division_file": v["kb_division_file"], "viewer": viewer_rel})
    for sec, v in specs.items():
        recs.append({"_kind": "spec", "section": sec, "title": v["title"], "csi_division": v["division"],
                     "atlas_sheets": v["atlas_sheets"], "kb_chunks": v["kb_chunks"], "viewer": viewer_rel})
    return interlinks, recs


def write_if_changed(path, obj):
    """Atomic write; returns True when the content changed."""
    path = Path(path)
    new = json.dumps(obj, indent=1, sort_keys=True)
    if path.exists() and path.read_text() == new:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(new)
    tmp.replace(path)
    return True


def run(kb_dir, atlas_path, out_dir, viewer_rel, request_id="", ignition_dir=None):
    atlas = load_json(atlas_path)
    if not isinstance(atlas, dict) or not atlas.get("sheets"):
        raise SystemExit(f"{atlas_path}: no plans_atlas sheets to interlink")
    inter, recs = build(kb_dir, atlas, viewer_rel, request_id, ignition_dir)
    inter["built_at"] = None      # keep the file byte-stable between identical runs
    changed = write_if_changed(Path(out_dir) / "interlinks.json", inter)
    changed |= write_if_changed(Path(out_dir) / "atlas-chunks.json", recs)
    return inter["stats"], inter["needs_review"], changed


def selftest():
    tmp = Path(tempfile.mkdtemp(prefix="interlink-"))
    (tmp / "extracts").mkdir()
    kb = {"project": {"slug": "demo"}, "sheet_index": [
        {"sheet_number": "A101", "sheet_title": "First Floor Plan", "page_index": "0", "_doc": "set"},
        {"sheet_number": "A999", "sheet_title": "Phantom Sheet", "page_index": "9", "_doc": "set"}]}
    (tmp / "kb.json").write_text(json.dumps(kb))
    (tmp / "curation.json").write_text("{}")
    idx = [
        {"id": "demo:sheet:s1", "domain": "sheet", "record": kb["sheet_index"][0], "text": "A101", "doc": "set"},
        {"id": "demo:sheet:s2", "domain": "sheet", "record": kb["sheet_index"][1], "text": "A999", "doc": "set"},
        {"id": "demo:sheet_note:n1", "domain": "sheet_note", "record": {"sheet": "A-101", "text": "Demo wall"}, "text": "Demo wall"},
        {"id": "demo:submittal:u1", "domain": "submittal", "record": {"spec_section": "09 51 13", "csi_division": "09", "item": "ACT"}, "text": "ACT", "csi_division": "09"},
        {"id": "demo:scope_item:c1", "domain": "scope_item", "record": {"text": "Replace ceilings per A-101 and M-9"}, "text": "Replace ceilings per A-101 and M-9"},
        {"id": "demo:product:p1", "domain": "product", "record": {"name": "Lay-in tile", "csi_division": "09"}, "text": "Lay-in tile", "csi_division": "09"}]
    (tmp / "kb_index.jsonl").write_text("\n".join(json.dumps(x) for x in idx))
    atlas = {"sheets": [{"sheet_id": "A-101", "sheet_no": "A-101", "title": "FIRST FLOOR PLAN", "page": 1,
                         "source_doc": "set.pdf", "divisions": ["09"]},
                        {"sheet_id": "A-201", "sheet_no": "A-201", "title": "ELEVATIONS", "page": 2,
                         "source_doc": "set.pdf", "divisions": ["09"]}],
             "concepts": {"trades": [{"division": "09", "label": "Finishes", "sheet_ids": ["A-101", "A-201"],
                                      "spec_sections": ["09 51 13"]}],
                          "specs": [{"section": "09 51 13", "division": "09", "title": "ACT", "sheet_ids": ["A-101"]}]}}
    inter, recs = build(tmp, atlas, "Plans Atlas/plans-atlas.html", "rid")
    s = inter["sheets"]["A-101"]
    assert s["kb_sheet"]["chunk"] == "demo:sheet:s1" and s["kb_sheet"]["via"] == "sheet_number", s
    assert "demo:sheet_note:n1" in s["links"]["notes"], s["links"]
    assert "demo:submittal:u1" in s["links"]["submittals"], s["links"]
    assert "demo:scope_item:c1" in s["links"]["scope"], "text mention of a real sheet"
    assert not any(r["sheet_id"] == "M9" for refs in inter["chunk_backrefs"].values() for r in refs), "unknown sheet ignored"
    assert [u["sheet_number"] for u in inter["unmatched"]["kb_sheets"]] == ["A999"]
    assert inter["unmatched"]["atlas_sheets"] == ["A-201"]
    assert inter["chunk_backrefs"]["demo:product:p1"][0]["via"] == "division", "division fallback"
    assert s["viewer"] == "Plans Atlas/plans-atlas.html#sheet=A-101"
    assert {r["_kind"] for r in recs} == {"sheet", "division", "spec"}
    (tmp / "atlas.json").write_text(json.dumps(atlas))
    st1 = run(tmp, tmp / "atlas.json", tmp / "o", "v.html", "rid")
    st2 = run(tmp, tmp / "atlas.json", tmp / "o", "v.html", "rid")
    assert st1[2] is True and st2[2] is False, "second identical run must not rewrite files"
    print("interlink selftest passed:", tmp)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("build", help="Write interlinks.json and atlas-chunks.json.")
    r.add_argument("--kb", required=True, type=Path)
    r.add_argument("--atlas", required=True, type=Path, help="plans_atlas.json section.")
    r.add_argument("--out", required=True, type=Path)
    r.add_argument("--viewer", default="Plans Atlas/plans-atlas.html")
    r.add_argument("--request-id", default="")
    sub.add_parser("selftest")
    a = ap.parse_args()
    if a.cmd == "selftest":
        selftest()
        return
    stats, review, changed = run(a.kb, a.atlas, a.out, a.viewer, a.request_id)
    print(json.dumps({"status": "interlinked", "changed": changed, "stats": stats, "needs_review": review}, indent=2))


if __name__ == "__main__":
    main()
