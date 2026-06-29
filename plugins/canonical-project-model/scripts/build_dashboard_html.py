#!/usr/bin/env python3
"""
build_dashboard_html.py — render the Canonical Project Record into a self-contained,
animated HTML dashboard.

The Excel workbook (build_workbook.py) is the working deliverable; this is the
read-only "at a glance" view — a single .html file (no external requests, safe to
email or host) that an estimator/PM/admin can open in any browser. Same source of
truth (canonical-model.json), same CSI MasterFormat organization and division sort.

Design intent (kept deliberately un-AI-slop): one disciplined brand accent on a
near-black ground, a real type/space scale, motion that means something (scroll
reveal, count-up, a working division filter that animates list changes, glow-on-hover
controls, a slow drifting background), and full `prefers-reduced-motion` support.

Stdlib only. Two modes:
  (default)    a complete standalone HTML document
  --fragment   body content only (style + markup + script), for embedding in a host
               that already provides <html>/<head>/<body> (e.g. an Artifact)
"""

import argparse
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN_DIR = HERE.parent
DIVISIONS_FILE = PLUGIN_DIR / "resources" / "masterformat-divisions.json"

DEFAULT_COMPANY = "NTXP"

# A cohesive blue-gray ramp indexed by MasterFormat division — distinguishable for
# scanning but on-palette (no rainbow). The division NUMBER is the real identifier;
# the swatch is a quiet secondary cue. Stays within the charcoal/blue/gold system.
DIV_PALETTE = [
    "#5b7fa6", "#6d8eb0", "#7f8aa0", "#8893a6", "#5f7286", "#6f8497",
    "#7d8fa4", "#8aa1b8", "#9aa6b3", "#647689", "#74849a", "#8796a0",
    "#9aa2ab", "#a7adb6",
]


def log(msg):
    sys.stderr.write(msg + "\n")


# --------------------------------------------------------------- data helpers

def load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception as e:  # noqa: BLE001
        log(f"could not read {path}: {e}")
        return None


def load_division_titles():
    data = load_json(DIVISIONS_FILE) or {}
    return {d["division"]: d["title"] for d in data.get("divisions", [])}


def resolve_section(model_dir, value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return load_json(Path(model_dir) / value) or {}
    return {}


def div_of(obj):
    if not isinstance(obj, dict):
        return "99"
    csi = obj.get("csi")
    if isinstance(csi, dict) and csi.get("masterformat_division"):
        return str(csi["masterformat_division"])
    if obj.get("masterformat_division"):
        return str(obj["masterformat_division"])
    divs = obj.get("csi_divisions")
    if isinstance(divs, list) and divs:
        return str(divs[0])
    return "99"


def div_key(obj):
    d = div_of(obj)
    try:
        return (int(d), d)
    except (ValueError, TypeError):
        return (99, "99")


def div_color(div):
    try:
        return DIV_PALETTE[int(div) % len(DIV_PALETTE)]
    except (ValueError, TypeError):
        return "#6E7B8B"


def money(obj):
    if isinstance(obj, dict) and isinstance(obj.get("amount"), (int, float)):
        return obj["amount"]
    return None


def qty_value(q):
    if isinstance(q, dict) and isinstance(q.get("value"), (int, float)):
        return q["value"]
    return None


def qty_uom(q):
    if isinstance(q, dict):
        return q.get("uom") or q.get("as_written") or ""
    return ""


def esc(v):
    return html.escape("" if v is None else str(v))


def fmt_money(amount):
    return f"${amount:,.0f}" if isinstance(amount, (int, float)) else "—"


# --------------------------------------------------------------------- styles

STYLE = """
:root{
  --bg:#191c21; --bg2:#15181c; --ink:#e9ecf1; --muted:#a3acb9; --faint:#6f7885;
  /* tight, semantic palette: blue=interactive/data, gold=rule/brand/money, red=risk */
  --blue:#5b9bd5; --blue-deep:#3f7cb8; --gold:#c8a050; --gold-soft:#d8b878; --red:#cf5c6b;
  --line-w:rgba(255,255,255,.09);            /* white hairline */
  --line-g:rgba(200,160,80,.45);             /* gold hairline */
  --line2:rgba(255,255,255,.16);
  /* 3D gradient surfaces (charcoal, beveled) */
  --panel:linear-gradient(157deg,#2b313a 0%,#23272f 52%,#1d2127 100%);
  --panel-hi:linear-gradient(157deg,#323945 0%,#262b34 55%,#1f242b 100%);
  --raise:0 1px 0 rgba(255,255,255,.05) inset,0 18px 38px -20px rgba(0,0,0,.85);
  --raise-hi:0 1px 0 rgba(255,255,255,.08) inset,0 24px 52px -18px rgba(0,0,0,.9),0 0 30px -6px rgba(91,155,213,.30);
  --r:14px;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  --sans:ui-sans-serif,-apple-system,"Segoe UI",Roboto,Inter,Helvetica,Arial,sans-serif;
  --serif:Georgia,"Iowan Old Style","Times New Roman",serif;
}
*{box-sizing:border-box}
.cpm-root{font-family:var(--sans);color:var(--ink);line-height:1.55;
  background:var(--bg);-webkit-font-smoothing:antialiased;position:relative;overflow-x:hidden}
.cpm-root h1,.cpm-root h2,.cpm-root h3{margin:0;font-weight:600;letter-spacing:-.01em}
.cpm-root a{color:inherit;text-decoration:none}
/* charcoal ground with 3D depth (radial vignette) + drifting blue/gold light */
.cpm-bg{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden;background:
  radial-gradient(120% 90% at 50% -10%,#222730 0%,#191c21 45%,#121419 100%)}
.cpm-bg::before,.cpm-bg::after{content:"";position:absolute;width:62vmax;height:62vmax;
  border-radius:50%;filter:blur(90px);opacity:.16;will-change:transform}
.cpm-bg::before{background:radial-gradient(circle,var(--blue),transparent 60%);top:-22vmax;right:-12vmax;
  animation:drift1 38s ease-in-out infinite}
.cpm-bg::after{background:radial-gradient(circle,var(--gold),transparent 60%);bottom:-26vmax;left:-16vmax;
  animation:drift2 46s ease-in-out infinite}
.cpm-grid{position:fixed;inset:0;z-index:0;pointer-events:none;opacity:.6;
  background-image:linear-gradient(rgba(255,255,255,.045) 1px,transparent 1px),
    linear-gradient(90deg,rgba(91,155,213,.05) 1px,transparent 1px);
  background-size:46px 46px;mask-image:radial-gradient(circle at 50% -5%,#000 0%,transparent 72%)}
@keyframes drift1{50%{transform:translate(-7vmax,6vmax) scale(1.12)}}
@keyframes drift2{50%{transform:translate(7vmax,-5vmax) scale(1.06)}}

.cpm-wrap{position:relative;z-index:1;max-width:1180px;margin:0 auto;padding:0 28px 110px}
.cpm-nav{position:sticky;top:0;z-index:20;display:flex;gap:6px;flex-wrap:wrap;align-items:center;
  padding:13px 28px;margin:0 -28px;backdrop-filter:blur(13px);
  background:linear-gradient(180deg,rgba(20,23,27,.9),rgba(20,23,27,.6));
  border-bottom:1px solid var(--line-w);box-shadow:0 1px 0 var(--line-g)}
.cpm-nav .brand{font:600 15px/1 var(--serif);letter-spacing:.01em;margin-right:auto;display:flex;align-items:center;gap:11px}
.cpm-nav .dot{width:9px;height:9px;border-radius:50%;background:var(--gold);
  box-shadow:0 0 10px var(--gold);animation:pulse 2.8s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(200,160,80,.5)}70%{box-shadow:0 0 0 9px rgba(200,160,80,0)}100%{box-shadow:0 0 0 0 rgba(200,160,80,0)}}
.cpm-nav a{font-size:13px;color:var(--muted);padding:7px 13px;border-radius:9px;transition:.22s ease;border:1px solid transparent}
.cpm-nav a:hover{color:#fff;border-color:var(--line2);box-shadow:0 0 20px -2px rgba(91,155,213,.45);transform:translateY(-1px)}

.cpm-hero{padding:60px 0 20px}
.cpm-eyebrow{font:600 12px/1 var(--mono);letter-spacing:.24em;text-transform:uppercase;color:var(--gold)}
.cpm-hero h1{font-family:var(--serif);font-size:clamp(30px,4.6vw,50px);line-height:1.05;margin:16px 0 8px}
.cpm-sub{color:var(--muted);font-size:15px}
.cpm-chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}
.cpm-chip{font:600 12px/1 var(--sans);padding:8px 13px;border-radius:999px;border:1px solid var(--line-w);
  background:var(--panel);box-shadow:var(--raise);color:var(--muted);display:inline-flex;gap:7px;align-items:center}
.cpm-chip b{color:var(--ink);font-weight:600}
.cpm-chip.joc{border-color:var(--line-g);color:var(--gold-soft)}

.cpm-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(178px,1fr));gap:16px;margin-top:30px}
.cpm-kpi{position:relative;padding:22px;border:1px solid var(--line-w);border-radius:var(--r);
  background:var(--panel);box-shadow:var(--raise);overflow:hidden;transition:.28s cubic-bezier(.2,.7,.2,1)}
.cpm-kpi:hover{transform:translateY(-4px);border-color:rgba(91,155,213,.4);box-shadow:var(--raise-hi)}
.cpm-kpi .label{font:600 11px/1 var(--mono);color:var(--faint);letter-spacing:.12em;text-transform:uppercase}
.cpm-kpi .val{font:700 32px/1.1 var(--sans);margin-top:12px;font-variant-numeric:tabular-nums}
.cpm-kpi .val.accent{color:var(--gold-soft)}
.cpm-kpi::after{content:"";position:absolute;left:0;right:0;top:0;height:2px;
  background:linear-gradient(90deg,transparent,var(--blue),transparent);opacity:0;transition:opacity .28s ease}
.cpm-kpi:hover::after{opacity:.85}

.cpm-section{margin-top:60px}
.cpm-section>h2{font-family:var(--serif);font-size:24px;display:flex;align-items:center;gap:13px;
  padding-bottom:12px;border-bottom:1px solid var(--line-w);
  background:linear-gradient(90deg,var(--line-g),transparent) bottom/40% 1px no-repeat}
.cpm-section>h2::before{content:"";width:20px;height:3px;background:var(--gold);border-radius:2px;box-shadow:0 0 10px var(--gold)}
.cpm-section .hint{color:var(--faint);font-size:13px;margin:10px 0 20px}

.cpm-card{border:1px solid var(--line-w);border-radius:var(--r);background:var(--panel);box-shadow:var(--raise);overflow:hidden}
.cpm-table{width:100%;border-collapse:collapse;font-size:14px}
.cpm-table th{text-align:left;font:600 11px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;
  color:var(--faint);padding:14px 16px;border-bottom:1px solid var(--line-g);
  background:linear-gradient(180deg,rgba(255,255,255,.04),transparent)}
.cpm-table td{padding:13px 16px;border-bottom:1px solid var(--line-w);vertical-align:top}
.cpm-table tr:last-child td{border-bottom:0}
.cpm-table tbody tr{transition:background .18s ease}
.cpm-table tbody tr:hover{background:rgba(91,155,213,.06)}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums}

.divtag{display:inline-flex;align-items:center;gap:8px;font:600 12px/1 var(--mono);
  padding:5px 10px;border-radius:7px;background:rgba(255,255,255,.04);border:1px solid var(--line-w);white-space:nowrap}
.divtag .sw{width:9px;height:9px;border-radius:3px;box-shadow:0 0 0 1px rgba(0,0,0,.3) inset}

.cpm-filter{display:flex;flex-wrap:wrap;gap:9px;margin:0 0 18px}
.fbtn{cursor:pointer;font:600 12px/1 var(--sans);color:var(--muted);background:var(--panel);
  border:1px solid var(--line-w);box-shadow:var(--raise);padding:9px 14px;border-radius:9px;transition:.2s ease}
.fbtn:hover{color:#fff;box-shadow:var(--raise),0 0 18px -2px rgba(91,155,213,.5);transform:translateY(-1px)}
.fbtn[aria-pressed="true"]{color:#fff;border-color:rgba(91,155,213,.6);
  background:linear-gradient(180deg,var(--blue),var(--blue-deep));box-shadow:0 0 22px -2px rgba(91,155,213,.6)}

.cpm-list{display:grid;gap:14px}
.tile{border:1px solid var(--line-w);border-radius:12px;background:var(--panel);box-shadow:var(--raise);
  padding:18px 20px;transition:.26s cubic-bezier(.2,.7,.2,1);position:relative}
.tile:hover{transform:translateY(-3px);border-color:rgba(91,155,213,.4);box-shadow:var(--raise-hi)}
.tile .top{display:flex;align-items:center;gap:13px;flex-wrap:wrap}
.tile .name{font-weight:600;font-size:15px}
.tile .sum{color:var(--muted);font-size:13.5px;margin-top:9px}
.tile .est{margin-left:auto;font:700 17px/1 var(--mono);color:var(--gold-soft)}
.bar{height:7px;border-radius:7px;background:rgba(0,0,0,.35);margin-top:13px;overflow:hidden;
  box-shadow:0 1px 0 rgba(255,255,255,.05)}
.bar>i{display:block;height:100%;border-radius:7px;width:0;
  background:linear-gradient(90deg,var(--blue-deep),var(--blue) 60%,var(--gold-soft));
  box-shadow:0 0 12px -2px rgba(91,155,213,.6);transition:width 1.1s cubic-bezier(.2,.7,.2,1)}

.meter{height:8px;border-radius:8px;background:rgba(0,0,0,.35);overflow:hidden;min-width:96px;box-shadow:0 1px 0 rgba(255,255,255,.05)}
.meter>i{display:block;height:100%;width:0;border-radius:8px;transition:width 1s ease}
.pill{font:600 11px/1 var(--mono);padding:5px 9px;border-radius:6px;border:1px solid var(--line-w);color:var(--muted)}
.pill.yes{color:var(--blue);border-color:rgba(91,155,213,.45)}
.pill.no{color:var(--faint)}

.rank{font:700 14px/1 var(--mono);color:var(--gold);width:32px;height:32px;flex:0 0 32px;
  display:grid;place-items:center;border:1px solid var(--line-g);border-radius:8px;
  background:linear-gradient(180deg,rgba(200,160,80,.12),transparent)}
.driver{font:600 11px/1 var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--muted);
  padding:5px 9px;border-radius:6px;background:rgba(255,255,255,.04);border:1px solid var(--line-w)}
.driver.risk{color:var(--red);border-color:rgba(207,92,107,.45);background:rgba(207,92,107,.08)}

.alt{border-left:3px solid var(--gold);padding:12px 16px;background:linear-gradient(90deg,rgba(200,160,80,.08),transparent);border-radius:0 10px 10px 0}
.review{border:1px solid rgba(207,92,107,.4);background:linear-gradient(160deg,rgba(207,92,107,.10),rgba(207,92,107,.03));
  border-radius:var(--r);padding:20px 22px;box-shadow:var(--raise)}
.review li{color:#edb4bc}

.timeline{position:relative;padding-left:28px}
.timeline::before{content:"";position:absolute;left:9px;top:5px;bottom:5px;width:2px;
  background:linear-gradient(var(--gold),var(--blue),transparent)}
.tl-item{position:relative;padding:0 0 20px 0}
.tl-item::before{content:"";position:absolute;left:-23px;top:5px;width:12px;height:12px;border-radius:50%;
  background:var(--bg);border:2px solid var(--gold);box-shadow:0 0 12px rgba(200,160,80,.55)}
.tl-item .d{font:600 12px/1 var(--mono);color:var(--gold-soft)}
.tl-item .l{margin-top:5px}

.total-row{display:flex;align-items:center;justify-content:space-between;margin-top:16px;padding:20px 24px;
  border-radius:var(--r);border:1px solid var(--line-g);box-shadow:var(--raise);
  background:linear-gradient(160deg,rgba(200,160,80,.10),rgba(91,155,213,.05) 60%,transparent)}
.total-row .t{font:600 12px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.total-row .v{font:700 28px/1 var(--mono);color:var(--gold-soft)}

.cpm-foot{margin-top:72px;padding-top:24px;border-top:1px solid var(--line-w);
  background:linear-gradient(90deg,var(--line-g),transparent) top/30% 1px no-repeat;color:var(--faint);font-size:12.5px}

.reveal{opacity:0;transform:translateY(16px);transition:opacity .6s ease,transform .6s cubic-bezier(.2,.7,.2,1)}
.reveal.in{opacity:1;transform:none}
.is-hidden{display:none!important}
@media (prefers-reduced-motion:reduce){
  *{animation:none!important;transition:none!important}
  .reveal{opacity:1;transform:none}
}
"""

SCRIPT = """
(function(){
  var rm = window.matchMedia && window.matchMedia('(prefers-reduced-motion:reduce)').matches;

  // Count-up. The element already shows its REAL value (correct with no JS / if never
  // scrolled to). When animated, we reset to 0 and climb — done while the element is
  // still faded out by .reveal, so the reset never flashes.
  function countUp(el){
    if(el.getAttribute('data-done'))return; el.setAttribute('data-done','1');
    var t=parseFloat(el.getAttribute('data-target')||'0'),
        pre=el.getAttribute('data-pre')||'', suf=el.getAttribute('data-suf')||'',
        dec=parseInt(el.getAttribute('data-dec')||'0',10),
        fmt=function(v){return pre+v.toLocaleString(undefined,{minimumFractionDigits:dec,maximumFractionDigits:dec})+suf;};
    if(rm){el.textContent=fmt(t);return;}
    var s=null,dur=1100;
    function step(ts){ s=s||ts; var p=Math.min((ts-s)/dur,1); var e=1-Math.pow(1-p,3);
      el.textContent=fmt(t*e); if(p<1)requestAnimationFrame(step);}
    requestAnimationFrame(step);
  }

  function fire(el){
    el.classList.add('in');
    el.querySelectorAll('[data-target]').forEach(countUp);
    el.querySelectorAll('[data-w]').forEach(function(b){ b.style.width=b.getAttribute('data-w'); });
  }

  var io = ('IntersectionObserver' in window) && !rm ? new IntersectionObserver(function(es){
    es.forEach(function(e){ if(e.isIntersecting){
      var el=e.target, d=parseInt(el.getAttribute('data-delay')||'0',10);
      setTimeout(function(){fire(el);},d); io.unobserve(el);
    }});
  },{threshold:.12}) : null;
  document.querySelectorAll('.reveal').forEach(function(el){ io?io.observe(el):fire(el); });

  // Failsafe: anything never scrolled into view still ends correct after a beat.
  setTimeout(function(){
    document.querySelectorAll('[data-target]:not([data-done])').forEach(countUp);
    document.querySelectorAll('[data-w]').forEach(function(b){ if(!b.style.width)b.style.width=b.getAttribute('data-w'); });
  }, 2600);

  // Division filter — animated list changes.
  document.querySelectorAll('.cpm-filter').forEach(function(bar){
    bar.addEventListener('click',function(ev){
      var b=ev.target.closest('.fbtn'); if(!b)return;
      var d=b.getAttribute('data-div'), scope=bar.getAttribute('data-scope');
      bar.querySelectorAll('.fbtn').forEach(function(x){x.setAttribute('aria-pressed', x===b?'true':'false');});
      document.querySelectorAll('[data-filterable="'+scope+'"]').forEach(function(row){
        row.classList.toggle('is-hidden', !(d==='all' || row.getAttribute('data-div')===d));
      });
    });
  });
})();
"""


# ------------------------------------------------------------------ rendering

def chip(label, value, cls=""):
    return f'<span class="cpm-chip {cls}">{esc(label)} <b>{esc(value)}</b></span>'


def divtag(div, titles):
    t = titles.get(div, "")
    return (f'<span class="divtag"><span class="sw" style="background:{div_color(div)}"></span>'
            f'{esc(div)}{(" · " + esc(t)) if t else ""}</span>')


def filter_bar(scope, divisions, titles):
    btns = ['<button class="fbtn" data-div="all" aria-pressed="true">All</button>']
    for d in divisions:
        btns.append(f'<button class="fbtn" data-div="{esc(d)}" aria-pressed="false">'
                    f'<span class="num">{esc(d)}</span> {esc(titles.get(d, ""))}</button>')
    return f'<div class="cpm-filter" data-scope="{scope}">{"".join(btns)}</div>'


def reveal(inner, delay=0, cls=""):
    return f'<div class="reveal {cls}" data-delay="{delay}">{inner}</div>'


def build_body(model, model_dir, company, titles):
    S = lambda k: resolve_section(model_dir, model.get("sections", {}).get(k, {}))
    proj = model.get("project", {})
    ident = S("project_identity")
    contacts = S("contacts").get("contacts", [])
    trades = sorted([t for t in S("trades").get("trades", []) if isinstance(t, dict)], key=div_key)
    qto = sorted([q for q in S("quantity_takeoff").get("items", []) if isinstance(q, dict)], key=div_key)
    budget = S("budget")
    blog = S("bid_log")
    crit = S("critical_path")
    subm = sorted([s for s in S("submittal_log").get("entries", []) if isinstance(s, dict)], key=div_key)
    sched = S("schedule")

    out = []

    # ---- nav ----
    nav = [f'<div class="brand"><span class="dot"></span>{esc(company)} · Canonical Project Record</div>']
    for nm, href in [("Overview", "#overview"), ("Trades", "#trades"), ("Takeoff", "#qto"),
                     ("Bids", "#bids"), ("Critical Path", "#critical"), ("Schedule", "#schedule"),
                     ("Budget", "#budget")]:
        nav.append(f'<a href="{href}">{nm}</a>')
    out.append(f'<nav class="cpm-nav">{"".join(nav)}</nav>')

    out.append('<div class="cpm-wrap">')

    # ---- hero ----
    chips = []
    if proj.get("number"): chips.append(chip("No.", proj["number"]))
    if proj.get("location"): chips.append(chip("Location", proj["location"]))
    if proj.get("delivery_method"): chips.append(chip("Delivery", str(proj["delivery_method"]).upper()))
    if proj.get("contract_type"): chips.append(chip("Contract", str(proj["contract_type"]).replace("_", " ")))
    if proj.get("is_joc"):
        joc = ident.get("joc", {}) if isinstance(ident.get("joc"), dict) else {}
        coef = joc.get("coefficient")
        chips.append(chip("JOC coeff.", coef if coef is not None else "—", "joc"))
    out.append(f'''<header class="cpm-hero" id="overview">
      <div class="cpm-eyebrow">Source of Truth · CSI MasterFormat</div>
      <h1>{esc(proj.get("title", "Untitled Project"))}</h1>
      <div class="cpm-sub">{esc(proj.get("owner", ""))}</div>
      <div class="cpm-chips">{"".join(chips)}</div>
    </header>''')

    # ---- KPIs ----
    conf = (model.get("confidence") or {}).get("overall")
    # Estimated value per trade: prefer the stated trades.estimated_value; otherwise
    # derive it from the budget lines (sum of qty x unit_cost) — the same number the
    # workbook computes with formulas — so the view isn't all zeros when only line
    # detail exists.
    budget_lines = [b for b in budget.get("lines", []) if isinstance(b, dict)]
    derived = {}
    for b in budget_lines:
        tid = b.get("trade_id")
        qv = qty_value(b.get("quantity"))
        uc = money(b.get("unit_cost"))
        ext = money(b.get("extended_cost"))
        amt = ext if ext is not None else ((qv * uc) if (qv is not None and uc is not None) else None)
        if tid and amt is not None:
            derived[tid] = derived.get(tid, 0) + amt
    def trade_est(tid):
        stated = money(next((t.get("estimated_value") for t in trades if t.get("trade_id") == tid), None))
        return stated if stated is not None else derived.get(tid)
    total_est = sum(v for v in (trade_est(t["trade_id"]) for t in trades) if v) or 0
    kpis = [
        ("Trades", len(trades), "", 0, ""),
        ("QTO lines", len(qto), "", 0, ""),
        ("Submittals", len(subm), "", 0, ""),
        ("Confidence", round((conf or 0) * 100), "", 0, "%"),
        ("Est. value", total_est, "$", 0, ""),
    ]
    cells = []
    for i, (lab, val, pre, dec, suf) in enumerate(kpis):
        acc = " accent" if lab == "Est. value" else ""
        init = f"{pre}{val:,}{suf}"  # real value pre-rendered so it's correct without/before JS
        cells.append(reveal(f'''<div class="cpm-kpi">
          <div class="label">{esc(lab)}</div>
          <div class="val{acc} num" data-target="{val}" data-pre="{pre}" data-suf="{suf}" data-dec="{dec}">{init}</div>
          </div>''', delay=i * 60))
    out.append(f'<div class="cpm-kpis">{"".join(cells)}</div>')

    # ---- key dates timeline ----
    kd = [k for k in ident.get("key_dates", []) if isinstance(k, dict)]
    kd.sort(key=lambda k: k.get("date") or "9999")
    if kd:
        items = "".join(
            reveal(f'<div class="tl-item"><div class="d">{esc(k.get("date") or k.get("as_written") or "TBD")}</div>'
                   f'<div class="l">{esc(k.get("label", ""))}</div></div>', delay=i * 50)
            for i, k in enumerate(kd))
        out.append(f'''<section class="cpm-section"><h2>Key Dates</h2>
          <div class="timeline">{items}</div></section>''')

    # ---- trades (filterable) ----
    if trades:
        divs = sorted({div_of(t) for t in trades}, key=lambda d: int(d) if d.isdigit() else 99)
        maxv = max([trade_est(t["trade_id"]) or 0 for t in trades] + [1])
        tiles = []
        for i, t in enumerate(trades):
            d = div_of(t); est = trade_est(t["trade_id"])
            w = f'{round((est or 0) / maxv * 100)}%'
            esthtml = f'<span class="est">{fmt_money(est)}</span>' if est else ""
            tiles.append(reveal(
                f'''<div class="tile" data-filterable="trades" data-div="{esc(d)}">
                  <div class="top">{divtag(d, titles)}<span class="name">{esc(t.get("name",""))}</span>{esthtml}</div>
                  <div class="sum">{esc(t.get("scope_summary","") or "—")}</div>
                  <div class="bar"><i data-w="{w}"></i></div>
                </div>''', delay=i * 45))
        out.append(f'''<section class="cpm-section" id="trades"><h2>Subcontractor Trades</h2>
          <div class="hint">Every trade with scope, in CSI MasterFormat order. Filter by division.</div>
          {filter_bar("trades", divs, titles)}
          <div class="cpm-list">{"".join(tiles)}</div></section>''')

    # ---- QTO (filterable table) ----
    if qto:
        divs = sorted({div_of(q) for q in qto}, key=lambda d: int(d) if d.isdigit() else 99)
        rows = []
        for q in qto:
            d = div_of(q); qv = qty_value(q.get("quantity"))
            rows.append(f'''<tr data-filterable="qto" data-div="{esc(d)}">
              <td>{divtag(d, titles)}</td><td>{esc(q.get("description",""))}</td>
              <td class="num">{esc(f"{qv:,.0f}" if isinstance(qv,(int,float)) else "")}</td>
              <td class="num">{esc(qty_uom(q.get("quantity")))}</td>
              <td>{esc(q.get("location",""))}</td>
              <td class="num">{esc(q.get("takeoff_id",""))}</td></tr>''')
        out.append(f'''<section class="cpm-section" id="qto"><h2>Summary Quantity Takeoff</h2>
          <div class="hint">The single source of truth — every other view links to these quantities.</div>
          {filter_bar("qto", divs, titles)}
          {reveal('<div class="cpm-card"><table class="cpm-table"><thead><tr>'
                  '<th>Div</th><th>Description</th><th>Qty</th><th>UOM</th><th>Location</th><th>Takeoff&nbsp;ID</th>'
                  '</tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>')}
        </section>''')

    # ---- bid log ----
    bl_trades = {b.get("trade_id"): b for b in blog.get("trades", []) if isinstance(b, dict)}
    bids = sorted([b for b in blog.get("bids", []) if isinstance(b, dict)], key=div_key)
    if bl_trades or bids:
        rows = []
        for t in trades:
            bt = bl_trades.get(t["trade_id"], {})
            est = trade_est(t["trade_id"]) or money(bt.get("estimated_budget"))
            cs = bt.get("confidence_score")
            if isinstance(cs, (int, float)):
                csp = round(cs * 100)
                col = "var(--blue)" if cs >= .75 else ("var(--gold-soft)" if cs >= .5 else "var(--red)")
                conf_cell = (f'<div style="display:flex;align-items:center;gap:10px">'
                             f'<div class="meter"><i data-w="{csp}%" style="background:{col}"></i></div>'
                             f'<span class="num" style="color:{col}">{csp}%</span></div>')
            else:
                conf_cell = '<span class="num" style="color:var(--faint)">—</span>'
            rows.append(f'''<tr><td>{divtag(div_of(t), titles)}</td><td>{esc(t.get("name",""))}</td>
              <td class="num">{fmt_money(est)}</td><td>{conf_cell}</td></tr>''')
        out.append(f'''<section class="cpm-section" id="bids"><h2>Bid Log</h2>
          <div class="hint">Estimated budget and confidence per trade.</div>
          {reveal('<div class="cpm-card"><table class="cpm-table"><thead><tr>'
                  '<th>Div</th><th>Trade</th><th>Estimate</th><th>Confidence</th></tr></thead><tbody>'
                  + "".join(rows) + '</tbody></table></div>') if rows else ""}''')
        if bids:
            brows = []
            for b in bids:
                resp = b.get("responded")
                brows.append(f'''<tr><td>{divtag(div_of(b), titles)}</td><td>{esc(b.get("trade_id",""))}</td>
                  <td class="num">{esc(b.get("party_id",""))}</td>
                  <td><span class="pill {"yes" if b.get("invited") else "no"}">{"invited" if b.get("invited") else "—"}</span></td>
                  <td><span class="pill {"yes" if resp else "no"}">{"responded" if resp else "pending"}</span></td>
                  <td class="num">{fmt_money(money(b.get("bid_amount")))}</td></tr>''')
            out.append(reveal('<div class="cpm-card" style="margin-top:14px"><table class="cpm-table"><thead><tr>'
                              '<th>Div</th><th>Trade</th><th>Bidder</th><th>Invited</th><th>Status</th><th>Bid</th>'
                              '</tr></thead><tbody>' + "".join(brows) + '</tbody></table></div>'))
        out.append('</section>')

    # ---- critical path ----
    citems = sorted([c for c in crit.get("items", []) if isinstance(c, dict)], key=lambda c: c.get("rank", 999))
    if citems or crit.get("alternates"):
        lis = []
        risk_drivers = {"long_lead", "permit", "design_gap", "owner_decision"}
        for i, c in enumerate(citems):
            drv = str(c.get("driver", ""))
            drv_cls = "driver risk" if drv in risk_drivers else "driver"
            lis.append(reveal(
                f'''<div class="tile"><div class="top">
                  <span class="rank">{esc(c.get("rank",""))}</span>{divtag(div_of(c), titles)}
                  <span class="name">{esc(c.get("description",""))}</span>
                  <span class="{drv_cls}" style="margin-left:auto">{esc(drv.replace("_"," "))}</span></div>
                  <div class="sum">{esc(c.get("reason",""))}</div></div>''', delay=i * 55))
        alts = "".join(
            reveal(f'<div class="alt"><b>{esc(str(a.get("type","")).upper())}</b> — {esc(a.get("description",""))}'
                   f'<div class="sum">{esc(a.get("rationale",""))}</div></div>', delay=i * 55)
            for i, a in enumerate(crit.get("alternates", []) if isinstance(crit.get("alternates"), list) else []))
        out.append(f'''<section class="cpm-section" id="critical"><h2>Critical Path</h2>
          <div class="cpm-list">{"".join(lis)}</div>
          {('<div class="cpm-list" style="margin-top:14px">' + alts + '</div>') if alts else ''}</section>''')

    # ---- schedule ----
    ms = [m for m in sched.get("milestones", []) if isinstance(m, dict)]
    ms.sort(key=lambda m: m.get("date") or "9999")
    if ms:
        items = "".join(
            reveal(f'<div class="tl-item"><div class="d">{esc(m.get("date") or m.get("relative_to") or "TBD")}</div>'
                   f'<div class="l">{esc(m.get("label",""))}'
                   f'{" · contractual" if m.get("is_contractual") else ""}</div></div>', delay=i * 45)
            for i, m in enumerate(ms))
        dur = sched.get("contract_duration")
        out.append(f'''<section class="cpm-section" id="schedule"><h2>Schedule</h2>
          {f'<div class="hint">Contract duration: {esc(dur)}</div>' if dur else ''}
          <div class="timeline">{items}</div></section>''')

    # ---- budget rollup ----
    if trades:
        maxv = max([trade_est(t["trade_id"]) or 0 for t in trades] + [1])
        rows = []
        for i, t in enumerate(trades):
            est = trade_est(t["trade_id"]) or 0; d = div_of(t)
            rows.append(reveal(
                f'''<div class="tile" style="padding:14px 18px"><div class="top">
                  {divtag(d, titles)}<span class="name">{esc(t.get("name",""))}</span>
                  <span class="est">{fmt_money(est)}</span></div>
                  <div class="bar"><i data-w="{round(est/maxv*100)}%"></i></div>
                </div>''', delay=i * 45))
        out.append(f'''<section class="cpm-section" id="budget"><h2>Budget Rollup</h2>
          <div class="cpm-list">{"".join(rows)}</div>
          <div class="total-row reveal"><span class="t">Project total (estimate)</span>
            <span class="v num" data-target="{total_est}" data-pre="$">${total_est:,.0f}</span></div></section>''')

    # ---- needs review ----
    nr = model.get("needs_human_review", [])
    if nr:
        lis = "".join(f"<li>{esc(x)}</li>" for x in nr[:30])
        out.append(f'''<section class="cpm-section"><h2>Needs Human Review</h2>
          {reveal(f'<div class="review"><ul style="margin:0;padding-left:18px">{lis}</ul></div>')}</section>''')

    # ---- footer ----
    gen = esc(model.get("generated_at", ""))
    out.append(f'''<footer class="cpm-foot">
      Rendered from <span class="num">canonical-model.json</span> · classification: CSI MasterFormat ·
      {esc(len(qto))} takeoff lines · this view organizes and presents — it does not price, level, or decide.
      {(" · generated " + gen) if gen else ""}
    </footer>''')

    out.append('</div>')  # /wrap
    return "".join(out)


def build(args):
    model = load_json(args.model)
    if not model:
        log(f"could not load model: {args.model}"); sys.exit(2)
    model_dir = Path(args.model).resolve().parent
    titles = load_division_titles()
    body = build_body(model, model_dir, args.company, titles)
    bg = '<div class="cpm-bg"></div><div class="cpm-grid"></div>'

    # Safeguard: if JS never runs (disabled, or saved-to-PDF), reveal everything so the
    # record is never blank — motion is an enhancement, the content is the point.
    noscript = '<noscript><style>.reveal{opacity:1!important;transform:none!important}' \
               '.bar>i,.meter>i{width:var(--fallback,60%)}</style></noscript>'

    if args.fragment:
        doc = f'<style>{STYLE}</style>{noscript}\n<div class="cpm-root">{bg}{body}</div>\n<script>{SCRIPT}</script>'
    else:
        title = esc(model.get("project", {}).get("title", "Project Dashboard"))
        doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
               f'<meta name="viewport" content="width=device-width,initial-scale=1">'
               f'<title>{title} · {esc(args.company)}</title>'
               f'<style>{STYLE}</style>{noscript}</head>'
               f'<body class="cpm-root">{bg}{body}<script>{SCRIPT}</script></body></html>')

    out = Path(args.out) if args.out else model_dir / f'{model.get("project", {}).get("slug", "project")}.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc)
    log(f"wrote dashboard: {out}  ({len(doc):,} bytes, {'fragment' if args.fragment else 'standalone'})")
    print(json.dumps({"dashboard": str(out), "bytes": len(doc), "mode": "fragment" if args.fragment else "standalone"}, indent=2))


def main():
    ap = argparse.ArgumentParser(description="Render the Canonical Project Record to an animated HTML dashboard.")
    ap.add_argument("--model", required=True, help="Path to canonical-model.json.")
    ap.add_argument("--out", help="Output .html path (default <model_dir>/<slug>.html).")
    ap.add_argument("--company", default=DEFAULT_COMPANY, help="Branding/company name (default NTXP).")
    ap.add_argument("--fragment", action="store_true",
                    help="Emit body content only (style+markup+script) for embedding in a host page.")
    build(ap.parse_args())


if __name__ == "__main__":
    main()
