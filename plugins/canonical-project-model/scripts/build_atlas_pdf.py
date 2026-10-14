#!/usr/bin/env python3
"""Embed the Plans Atlas navigation into the drawing-set PDF itself.

Reads sections/plans_atlas.json and writes a new PDF in which:
  * every verified sheet-callout link becomes a live link to its target sheet;
  * Plans Atlas index pages (Letter portrait) are appended AFTER the last
    drawing, so no original page number, bookmark or link target shifts:
    by trade (CSI division), by spec section, by area, and a full sheet index,
    every entry a live link to its sheet;
  * a "Plans Atlas Index" bookmark is added to the existing outline.
The source PDF is never modified. Original links, bookmarks and annotations
are carried over untouched. Requires PyMuPDF.

    python build_atlas_pdf.py --pdf set.pdf --model <project>/model --out set-v2.pdf
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # older PyMuPDF
    import fitz

NAVY = (0.09, 0.19, 0.33)
GOLD = (0.74, 0.58, 0.25)
INK = (0.12, 0.14, 0.18)
MUTED = (0.38, 0.42, 0.48)
LINK = (0.10, 0.34, 0.66)
PW, PH, MARGIN = 612, 792, 40


def log(msg):
    sys.stderr.write(f"[atlas-pdf] {msg}\n")


class Index:
    """Letter-portrait flowing layout with clickable chips."""

    def __init__(self, doc, title, subtitle):
        self.doc, self.title, self.subtitle = doc, title, subtitle
        self.pages = []
        self.links = []          # (page_index, rect, target_page_index)
        self.page = None
        self.y = 0
        self.new_page()

    def new_page(self):
        self.page = self.doc.new_page(width=PW, height=PH)
        self.pages.append(self.page)
        p = self.page
        p.draw_rect(fitz.Rect(0, 0, PW, 58), color=NAVY, fill=NAVY)
        p.draw_rect(fitz.Rect(0, 58, PW, 62), color=GOLD, fill=GOLD)
        # centered, full-width header
        p.insert_textbox(fitz.Rect(0, 12, PW, 36), self.title, fontname="hebo",
                         fontsize=17, color=(1, 1, 1), align=1)
        p.insert_textbox(fitz.Rect(0, 36, PW, 54), self.subtitle, fontname="helv",
                         fontsize=8.5, color=(0.82, 0.87, 0.94), align=1)
        n = len(self.pages)
        p.insert_text((MARGIN, PH - 22), "NTXP Plans Atlas | organizes only; the stamped drawings govern",
                      fontname="helv", fontsize=7, color=MUTED)
        p.insert_text((PW - MARGIN - 40, PH - 22), f"Index p.{n}", fontname="helv", fontsize=7, color=MUTED)
        self.y = 82

    def ensure(self, h):
        if self.y + h > PH - 44:
            self.new_page()

    def heading(self, text, count=None):
        self.ensure(40)
        self.y += 8
        p = self.page
        p.draw_rect(fitz.Rect(MARGIN, self.y, PW - MARGIN, self.y + 20), color=None, fill=(0.93, 0.95, 0.98))
        p.draw_rect(fitz.Rect(MARGIN, self.y, MARGIN + 4, self.y + 20), color=None, fill=GOLD)
        p.insert_text((MARGIN + 10, self.y + 14), text, fontname="hebo", fontsize=10.5, color=NAVY)
        if count is not None:
            p.insert_text((PW - MARGIN - 90, self.y + 14), f"{count} sheets", fontname="helv", fontsize=8, color=MUTED)
        self.y += 28

    def label(self, text, sub=None):
        self.ensure(26)
        self.page.insert_text((MARGIN + 6, self.y + 9), text, fontname="hebo", fontsize=8.5, color=INK)
        if sub:
            w = fitz.get_text_length(text, fontname="hebo", fontsize=8.5)
            self.page.insert_text((MARGIN + 12 + w, self.y + 9), sub, fontname="helv", fontsize=7.5, color=MUTED)
        self.y += 13

    def chips(self, items, target_of):
        """items: sheet ids. Wraps; each chip links to the sheet's page."""
        x, line_h = MARGIN + 14, 13
        for sid in items:
            tp = target_of(sid)
            if tp is None:
                continue          # sheet belongs to another source PDF
            w = fitz.get_text_length(sid, fontname="helv", fontsize=7.5) + 8
            if x + w > PW - MARGIN:
                x = MARGIN + 14
                self.y += line_h
            self.ensure(line_h + 4)
            r = fitz.Rect(x, self.y, x + w, self.y + 11)
            self.page.draw_rect(r, color=(0.74, 0.80, 0.90), fill=(0.97, 0.98, 1.0), width=0.5)
            self.page.insert_text((x + 4, self.y + 8.3), sid, fontname="helv", fontsize=7.5, color=LINK)
            if tp is not None:
                self.links.append((len(self.pages) - 1, r, tp))
            x += w + 4
        self.y += line_h + 5

    def bars(self, rows):
        """rows: (label, count). Simple horizontal bar infographic."""
        top = max([c for _, c in rows] or [1]) or 1
        for lab, c in rows:
            self.ensure(14)
            self.page.insert_text((MARGIN + 6, self.y + 8), lab[:34], fontname="helv", fontsize=7.5, color=INK)
            bw = max(2, 300 * c / top)
            self.page.draw_rect(fitz.Rect(MARGIN + 190, self.y, MARGIN + 190 + bw, self.y + 9), color=None, fill=NAVY)
            self.page.insert_text((MARGIN + 196 + bw, self.y + 8), str(c), fontname="hebo", fontsize=7.5, color=INK)
            self.y += 13
        self.y += 6

    def row(self, left, mid, page_no, target):
        self.ensure(13)
        p = self.page
        p.insert_text((MARGIN + 6, self.y + 9), left, fontname="hebo", fontsize=8, color=LINK)
        p.insert_text((MARGIN + 74, self.y + 9), mid[:78], fontname="helv", fontsize=8, color=INK)
        p.insert_text((PW - MARGIN - 34, self.y + 9), f"p.{page_no}", fontname="helv", fontsize=7.5, color=MUTED)
        r = fitz.Rect(MARGIN, self.y, PW - MARGIN, self.y + 12)
        self.links.append((len(self.pages) - 1, r, target))
        self.y += 12.5


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--model", required=True, type=Path, help="project model/ dir holding sections/plans_atlas.json")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--project", default="", help="Project name for the index header.")
    a = ap.parse_args()

    atlas = json.loads((a.model / "sections" / "plans_atlas.json").read_text())
    doc = fitz.open(str(a.pdf))
    n_orig = doc.page_count
    toc_before = doc.get_toc()
    # Page numbers restart at 1 in every source PDF; only this PDF's sheets map here.
    sheets = [x for x in atlas["sheets"] if x.get("source_doc") == a.pdf.name]
    if not sheets:
        sys.exit(f"no sheets in plans_atlas.json come from {a.pdf.name}; run deploy_atlas.py on this set first")
    mine = {x["sheet_id"] for x in sheets}
    page_of = {}
    for s in sheets:
        pg = int(s.get("page") or 0)
        if 1 <= pg <= n_orig:
            page_of.setdefault(s["sheet_id"], pg - 1)
            page_of.setdefault(s["sheet_no"], pg - 1)

    # ---- 1. live callout links on the drawing pages ------------------------
    existing = {i: [fitz.Rect(l["from"]) for l in doc[i].get_links()] for i in range(n_orig)}
    added = skipped = 0
    why = {"unresolved": 0, "same_sheet": 0, "overlaps_original": 0}
    for l in atlas.get("links", []):
        if l.get("from_sheet") not in mine:
            continue
        src, dst = page_of.get(l.get("from_sheet")), page_of.get(l.get("to_sheet"))
        box = l.get("from_box")
        if src is None or dst is None or not box:
            skipped += 1
            why["unresolved"] += 1
            continue
        if src == dst:
            skipped += 1
            why["same_sheet"] += 1
            continue
        page = doc[src]
        W, H = page.rect.width, page.rect.height
        r = fitz.Rect(box[0] * W, box[1] * H, box[2] * W, box[3] * H)
        r = fitz.Rect(r.x0 - 2, r.y0 - 2, r.x1 + 2, r.y1 + 2) * page.derotation_matrix
        r.normalize()
        if any(r.intersects(e) for e in existing[src]):
            skipped += 1                       # never shadow an original link
            why["overlaps_original"] += 1
            continue
        page.insert_link({"kind": fitz.LINK_GOTO, "from": r, "page": dst,
                          "to": fitz.Point(0, 0), "zoom": 0})
        existing[src].append(r)
        added += 1
    log(f"callout links added {added}, skipped {skipped} {why}")

    # ---- 2. appended index pages -------------------------------------------
    name = a.project or atlas.get("source_set") or a.pdf.stem
    idx = Index(doc, "PLANS ATLAS INDEX", f"{name}  |  {len(sheets)} sheets  |  every entry is a live link")
    sheet_by_id = {s["sheet_id"]: s for s in sheets}
    target = lambda sid: page_of.get(sid)      # noqa: E731
    first_index_page = n_orig                  # 0-based index of first appended page

    idx.heading("Overview")
    div_rows = []
    trades = [t for t in atlas["concepts"].get("trades", []) if t.get("sheet_ids")]
    for t in trades:
        div_rows.append((f"Div {t['division']}  {t.get('label','')}", len(t["sheet_ids"])))
    idx.label("Sheets by trade (CSI MasterFormat division)")
    idx.bars(div_rows)

    idx.heading("By Trade (CSI Division)")
    for t in trades:
        idx.label(f"Division {t['division']} - {t.get('label','')}",
                  f"{len(t['sheet_ids'])} sheets" + (f"  |  specs: {', '.join(t['spec_sections'][:6])}" if t.get("spec_sections") else ""))
        idx.chips(sorted(t["sheet_ids"]), target)

    specs = [sp for sp in atlas["concepts"].get("specs", []) if sp.get("sheet_ids")]
    idx.heading("By Spec Section", len(specs))
    for sp in sorted(specs, key=lambda x: x["section"]):
        idx.label(f"Section {sp['section']}", f"Div {sp['division']}" + (f"  {sp['title']}" if sp.get("title") else ""))
        idx.chips(sorted(sp["sheet_ids"]), target)

    areas = atlas["concepts"].get("areas", [])
    if areas:
        idx.heading("By Area", len(areas))
        for ar in areas:
            idx.label(ar["area"], "divisions " + ", ".join(ar.get("divisions", [])))
            idx.chips(sorted(ar["sheet_ids"]), target)
    phases = atlas["concepts"].get("phases", [])
    if phases:
        idx.heading("By Phase", len(phases))
        for ph in phases:
            idx.label(f"Phase {ph.get('phase','')}")
            idx.chips(sorted(ph["sheet_ids"]), target)

    idx.heading("Sheet Index", len(sheets))
    for s in sorted(sheets, key=lambda s: int(s.get("page") or 0)):
        pg = int(s.get("page") or 0)
        if 1 <= pg <= n_orig:
            idx.row(s["sheet_no"], s.get("title", ""), pg, pg - 1)

    for pi, rect, tp in idx.links:
        doc[n_orig + pi].insert_link({"kind": fitz.LINK_GOTO, "from": rect, "page": tp,
                                      "to": fitz.Point(0, 0), "zoom": 0})
    # back-to-index link on every appended page (footer)
    for k in range(1, len(idx.pages)):
        pg = doc[n_orig + k]
        r = fitz.Rect(PW / 2 - 50, PH - 28, PW / 2 + 50, PH - 14)
        pg.insert_text((PW / 2 - 44, PH - 20), "Back to Index start", fontname="helv", fontsize=7, color=LINK)
        pg.insert_link({"kind": fitz.LINK_GOTO, "from": r, "page": first_index_page,
                                  "to": fitz.Point(0, 0), "zoom": 0})

    toc = toc_before + [[1, "Plans Atlas Index", first_index_page + 1]]
    doc.set_toc(toc)
    meta = dict(doc.metadata or {})
    meta["subject"] = (meta.get("subject") or "") + " | Plans Atlas v2 (links + index appended)"
    doc.set_metadata(meta)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(a.out), garbage=3, deflate=True)
    log(f"wrote {a.out}: {n_orig} drawing pages + {len(idx.pages)} index pages")
    print(json.dumps({"status": "built", "out": str(a.out), "drawing_pages": n_orig,
                      "index_pages": len(idx.pages), "callout_links_added": added}))


if __name__ == "__main__":
    main()
