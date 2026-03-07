#!/usr/bin/env python3
"""
Construction Submittal Tracker — Web Application
=================================================
Zero-dependency web app for JOC & public construction submittal management.

Usage:
    python app.py [--port 8080] [--host 0.0.0.0]

Opens automatically in your default browser.
"""

import http.server
import json
import os
import socketserver
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import argparse

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
CSI_DATA_FILE = DATA_DIR / "csi_submittal_types.json"
DB_FILE = DATA_DIR / "register_db.json"

VALID_STATUSES = [
    "Not Started", "In Preparation", "Submitted", "Under Review",
    "Approved", "Approved as Noted", "Revise & Resubmit", "Rejected",
    "For Record Only", "Closed",
]


def load_csi_data():
    with open(CSI_DATA_FILE) as f:
        return json.load(f)


def load_db():
    if DB_FILE.exists():
        with open(DB_FILE) as f:
            return json.load(f)
    return {"projects": [], "active_project": None}


def save_db(db):
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2, default=str)


def get_active_project(db):
    if db["active_project"] is not None:
        for p in db["projects"]:
            if p["id"] == db["active_project"]:
                return p
    return None


def next_submittal_number(submittals, division):
    existing = [s for s in submittals if s["division"] == division]
    seq = len(existing) + 1
    return f"{division}-{seq:03d}"


# ── HTML Frontend ──────────────────────────────────────────────────────────────

def get_html():
    return r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Construction Submittal Tracker</title>
<style>
:root {
  --bg: #0f1117;
  --surface: #1a1d27;
  --surface2: #242836;
  --border: #2e3345;
  --text: #e4e6f0;
  --text2: #8b8fa3;
  --accent: #5b8af5;
  --accent2: #3d6ae0;
  --green: #34d399;
  --yellow: #fbbf24;
  --orange: #f97316;
  --red: #ef4444;
  --purple: #a78bfa;
  --radius: 8px;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }
a { color:var(--accent); text-decoration:none; }

/* Layout */
.app { display:flex; min-height:100vh; }
.sidebar { width:240px; background:var(--surface); border-right:1px solid var(--border); padding:16px 0; display:flex; flex-direction:column; position:fixed; top:0; left:0; bottom:0; z-index:10; }
.main { margin-left:240px; flex:1; padding:24px 32px; min-height:100vh; }

.sidebar h1 { font-size:14px; font-weight:700; padding:0 16px 16px; color:var(--accent); letter-spacing:0.5px; text-transform:uppercase; border-bottom:1px solid var(--border); margin-bottom:8px; }
.sidebar h1 span { display:block; font-size:10px; color:var(--text2); font-weight:400; margin-top:2px; text-transform:none; letter-spacing:0; }
.nav-item { padding:10px 16px; cursor:pointer; font-size:13px; color:var(--text2); display:flex; align-items:center; gap:8px; transition:all 0.15s; }
.nav-item:hover { background:var(--surface2); color:var(--text); }
.nav-item.active { background:var(--accent2); color:#fff; }
.nav-item .icon { width:18px; text-align:center; }
.nav-section { font-size:10px; text-transform:uppercase; letter-spacing:1px; color:var(--text2); padding:16px 16px 6px; opacity:0.6; }
.sidebar-footer { margin-top:auto; padding:12px 16px; border-top:1px solid var(--border); font-size:11px; color:var(--text2); }

/* Header */
.page-header { margin-bottom:24px; }
.page-header h2 { font-size:22px; font-weight:600; }
.page-header p { font-size:13px; color:var(--text2); margin-top:4px; }

/* Cards */
.cards { display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:16px; margin-bottom:24px; }
.card { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:16px; }
.card .label { font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:var(--text2); margin-bottom:4px; }
.card .value { font-size:28px; font-weight:700; }
.card .sub { font-size:11px; color:var(--text2); margin-top:2px; }
.card.green .value { color:var(--green); }
.card.yellow .value { color:var(--yellow); }
.card.orange .value { color:var(--orange); }
.card.red .value { color:var(--red); }
.card.blue .value { color:var(--accent); }
.card.purple .value { color:var(--purple); }

/* Tables */
.table-wrap { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; margin-bottom:24px; }
.table-toolbar { padding:12px 16px; display:flex; gap:10px; align-items:center; border-bottom:1px solid var(--border); flex-wrap:wrap; }
.table-toolbar input, .table-toolbar select { background:var(--surface2); border:1px solid var(--border); border-radius:6px; padding:6px 10px; font-size:12px; color:var(--text); outline:none; }
.table-toolbar input:focus, .table-toolbar select:focus { border-color:var(--accent); }
.table-toolbar input { width:220px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
thead { background:var(--surface2); }
th { padding:10px 12px; text-align:left; font-weight:600; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:var(--text2); white-space:nowrap; }
td { padding:10px 12px; border-top:1px solid var(--border); vertical-align:middle; }
tr:hover td { background:rgba(91,138,245,0.04); }
.mono { font-family:'SF Mono',Consolas,monospace; font-size:12px; }

/* Status badges */
.badge { display:inline-block; padding:3px 8px; border-radius:10px; font-size:11px; font-weight:600; white-space:nowrap; }
.badge-not-started { background:rgba(139,143,163,0.15); color:var(--text2); }
.badge-in-prep { background:rgba(251,191,36,0.15); color:var(--yellow); }
.badge-submitted { background:rgba(91,138,245,0.15); color:var(--accent); }
.badge-under-review { background:rgba(167,139,250,0.15); color:var(--purple); }
.badge-approved { background:rgba(52,211,153,0.15); color:var(--green); }
.badge-approved-noted { background:rgba(52,211,153,0.1); color:#6ee7b7; }
.badge-resubmit { background:rgba(249,115,22,0.15); color:var(--orange); }
.badge-rejected { background:rgba(239,68,68,0.15); color:var(--red); }
.badge-record { background:rgba(139,143,163,0.1); color:var(--text2); }
.badge-closed { background:rgba(52,211,153,0.08); color:#6ee7b7; }

/* Lead time indicator */
.lead-bar { height:6px; border-radius:3px; background:var(--surface2); width:80px; display:inline-block; vertical-align:middle; margin-right:6px; }
.lead-fill { height:100%; border-radius:3px; }
.lead-low .lead-fill { background:var(--green); }
.lead-med .lead-fill { background:var(--yellow); }
.lead-high .lead-fill { background:var(--orange); }
.lead-crit .lead-fill { background:var(--red); }

/* Buttons */
.btn { padding:7px 14px; border-radius:6px; font-size:12px; font-weight:600; cursor:pointer; border:1px solid var(--border); background:var(--surface2); color:var(--text); transition:all 0.15s; display:inline-flex; align-items:center; gap:6px; }
.btn:hover { background:var(--border); }
.btn-primary { background:var(--accent); border-color:var(--accent); color:#fff; }
.btn-primary:hover { background:var(--accent2); }
.btn-success { background:var(--green); border-color:var(--green); color:#000; }
.btn-danger { background:var(--red); border-color:var(--red); color:#fff; }
.btn-sm { padding:4px 10px; font-size:11px; }

/* Modal */
.modal-overlay { position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.6); z-index:100; display:none; align-items:center; justify-content:center; }
.modal-overlay.open { display:flex; }
.modal { background:var(--surface); border:1px solid var(--border); border-radius:12px; width:560px; max-width:95vw; max-height:90vh; overflow-y:auto; }
.modal-header { padding:16px 20px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; }
.modal-header h3 { font-size:16px; }
.modal-close { background:none; border:none; color:var(--text2); cursor:pointer; font-size:20px; }
.modal-body { padding:20px; }
.modal-footer { padding:12px 20px; border-top:1px solid var(--border); display:flex; justify-content:flex-end; gap:8px; }

/* Forms */
.form-group { margin-bottom:14px; }
.form-group label { display:block; font-size:12px; font-weight:600; color:var(--text2); margin-bottom:4px; }
.form-group input, .form-group select, .form-group textarea { width:100%; background:var(--surface2); border:1px solid var(--border); border-radius:6px; padding:8px 10px; font-size:13px; color:var(--text); outline:none; font-family:inherit; }
.form-group input:focus, .form-group select:focus, .form-group textarea:focus { border-color:var(--accent); }
.form-row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }

/* Chart bars */
.chart-bar-row { display:flex; align-items:center; gap:10px; margin-bottom:6px; }
.chart-label { width:140px; font-size:12px; color:var(--text2); text-align:right; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.chart-bar { height:22px; border-radius:4px; min-width:2px; transition:width 0.3s; display:flex; align-items:center; padding:0 8px; }
.chart-bar span { font-size:10px; font-weight:700; color:#fff; }
.chart-count { font-size:12px; color:var(--text2); min-width:30px; }

/* Progress ring */
.progress-ring { position:relative; width:80px; height:80px; margin:0 auto 8px; }
.progress-ring svg { transform:rotate(-90deg); }
.progress-ring circle { fill:none; stroke-width:6; }
.progress-ring .bg { stroke:var(--surface2); }
.progress-ring .fg { stroke:var(--green); stroke-linecap:round; transition:stroke-dashoffset 0.5s; }
.progress-pct { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); font-size:18px; font-weight:700; }

/* Responsive */
@media(max-width:900px) {
  .sidebar { width:56px; }
  .sidebar h1, .nav-item span, .nav-section, .sidebar-footer { display:none; }
  .nav-item { justify-content:center; padding:12px; }
  .main { margin-left:56px; padding:16px; }
}

/* Tabs */
.tabs { display:flex; gap:0; margin-bottom:20px; border-bottom:2px solid var(--border); }
.tab { padding:10px 18px; font-size:13px; font-weight:600; color:var(--text2); cursor:pointer; border-bottom:2px solid transparent; margin-bottom:-2px; transition:all 0.15s; }
.tab:hover { color:var(--text); }
.tab.active { color:var(--accent); border-bottom-color:var(--accent); }

/* Setup page */
.setup-card { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:32px; max-width:540px; margin:60px auto; }
.setup-card h2 { font-size:20px; margin-bottom:4px; }
.setup-card p { color:var(--text2); font-size:13px; margin-bottom:20px; }
.division-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(200px, 1fr)); gap:8px; margin:12px 0 20px; }
.div-check { display:flex; align-items:center; gap:6px; font-size:12px; padding:6px 8px; background:var(--surface2); border-radius:6px; cursor:pointer; }
.div-check:hover { background:var(--border); }
.div-check input { accent-color:var(--accent); }

.toast { position:fixed; bottom:24px; right:24px; background:var(--green); color:#000; padding:10px 18px; border-radius:8px; font-size:13px; font-weight:600; z-index:200; opacity:0; transition:opacity 0.3s; pointer-events:none; }
.toast.show { opacity:1; }
</style>
</head>
<body>
<div class="app" id="app">
  <!-- Sidebar -->
  <nav class="sidebar">
    <h1>Submittal Tracker <span>JOC / Public Construction</span></h1>
    <div class="nav-section">Main</div>
    <div class="nav-item active" data-page="dashboard" onclick="navigate('dashboard')"><span class="icon">&#9632;</span><span>Dashboard</span></div>
    <div class="nav-item" data-page="register" onclick="navigate('register')"><span class="icon">&#9776;</span><span>Register</span></div>
    <div class="nav-item" data-page="critical" onclick="navigate('critical')"><span class="icon">&#9888;</span><span>Critical Path</span></div>
    <div class="nav-section">Actions</div>
    <div class="nav-item" data-page="add" onclick="navigate('add')"><span class="icon">&#10010;</span><span>Add Submittal</span></div>
    <div class="nav-item" data-page="generate" onclick="navigate('generate')"><span class="icon">&#9881;</span><span>Generate</span></div>
    <div class="nav-item" data-page="scan" onclick="navigate('scan')"><span class="icon">&#128269;</span><span>Scan Specs</span></div>
    <div class="nav-section">Project</div>
    <div class="nav-item" data-page="settings" onclick="navigate('settings')"><span class="icon">&#9998;</span><span>Settings</span></div>
    <div class="nav-item" onclick="exportCSV()"><span class="icon">&#8681;</span><span>Export CSV</span></div>
    <div class="sidebar-footer">v1.0 &mdash; Zero Dependencies</div>
  </nav>

  <!-- Main content area -->
  <div class="main" id="main-content"></div>
</div>

<!-- Edit Modal -->
<div class="modal-overlay" id="editModal">
  <div class="modal">
    <div class="modal-header"><h3 id="editModalTitle">Edit Submittal</h3><button class="modal-close" onclick="closeModal()">&times;</button></div>
    <div class="modal-body" id="editModalBody"></div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="saveEdit()">Save Changes</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
// ── State ──
let STATE = { project: null, submittals: [], csi: null };
let currentPage = 'dashboard';
let editingId = null;

// ── API ──
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch('/api' + path, opts);
  return res.json();
}

async function loadState() {
  const data = await api('GET', '/state');
  STATE = data;
  if (!STATE.project) {
    navigate('settings');
  }
}

function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2500);
}

// ── Navigation ──
function navigate(page) {
  currentPage = page;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.page === page));
  render();
}

function render() {
  const el = document.getElementById('main-content');
  switch(currentPage) {
    case 'dashboard': el.innerHTML = renderDashboard(); break;
    case 'register': el.innerHTML = renderRegister(); break;
    case 'critical': el.innerHTML = renderCritical(); break;
    case 'add': el.innerHTML = renderAddForm(); break;
    case 'generate': el.innerHTML = renderGenerate(); break;
    case 'scan': el.innerHTML = renderScan(); break;
    case 'settings': el.innerHTML = renderSettings(); break;
  }
}

// ── Helpers ──
function statusBadge(status) {
  const cls = {
    'Not Started': 'badge-not-started', 'In Preparation': 'badge-in-prep',
    'Submitted': 'badge-submitted', 'Under Review': 'badge-under-review',
    'Approved': 'badge-approved', 'Approved as Noted': 'badge-approved-noted',
    'Revise & Resubmit': 'badge-resubmit', 'Rejected': 'badge-rejected',
    'For Record Only': 'badge-record', 'Closed': 'badge-closed'
  }[status] || 'badge-not-started';
  return `<span class="badge ${cls}">${status}</span>`;
}

function leadIndicator(weeks) {
  const maxW = 20;
  const pct = Math.min(weeks / maxW * 100, 100);
  let cls = 'lead-low';
  if (weeks >= 12) cls = 'lead-crit';
  else if (weeks >= 8) cls = 'lead-high';
  else if (weeks >= 4) cls = 'lead-med';
  return `<div class="lead-bar ${cls}"><div class="lead-fill" style="width:${pct}%"></div></div>${weeks}wk`;
}

function statusOptions(current) {
  const sts = ['Not Started','In Preparation','Submitted','Under Review','Approved','Approved as Noted','Revise & Resubmit','Rejected','For Record Only','Closed'];
  return sts.map(s => `<option value="${s}" ${s===current?'selected':''}>${s}</option>`).join('');
}

function typeLabel(code) {
  const map = {SD:'Shop Drawings',PD:'Product Data',SS:'Samples',CP:'Certificates',DI:'Design Info',MO:'Mockups',QC:'Quality Control',CL:'Closeout',WP:'Work Plan',SR:'Sustainable'};
  return map[code] || code;
}

// ── Dashboard ──
function renderDashboard() {
  const s = STATE.submittals;
  if (!STATE.project) return renderSettings();
  const total = s.length;
  if (!total) return `<div class="page-header"><h2>Dashboard</h2><p>${STATE.project.name}</p></div><div class="setup-card" style="text-align:center;"><h2>No submittals yet</h2><p>Generate from CSI data or add manually to get started.</p><button class="btn btn-primary" onclick="navigate('generate')">Generate Submittals</button></div>`;

  const approved = s.filter(x => ['Approved','Approved as Noted','Closed','For Record Only'].includes(x.status)).length;
  const pending = s.filter(x => ['Not Started','In Preparation'].includes(x.status)).length;
  const inReview = s.filter(x => ['Submitted','Under Review'].includes(x.status)).length;
  const action = s.filter(x => ['Revise & Resubmit','Rejected'].includes(x.status)).length;
  const critical = s.filter(x => x.lead_time_weeks >= 8 && !['Approved','Approved as Noted','Closed','For Record Only'].includes(x.status)).length;
  const pct = Math.round(approved / total * 100);

  // Status chart data
  const statusCounts = {};
  s.forEach(x => { statusCounts[x.status] = (statusCounts[x.status]||0) + 1; });
  const statusColors = {
    'Not Started':'#6b7280','In Preparation':'#fbbf24','Submitted':'#5b8af5','Under Review':'#a78bfa',
    'Approved':'#34d399','Approved as Noted':'#6ee7b7','Revise & Resubmit':'#f97316','Rejected':'#ef4444',
    'For Record Only':'#6b7280','Closed':'#34d399'
  };

  // Division chart
  const divCounts = {};
  s.forEach(x => { const k = x.division + ' ' + x.division_name; divCounts[k] = (divCounts[k]||0) + 1; });

  const circumference = 2 * Math.PI * 35;
  const offset = circumference - (pct / 100) * circumference;

  let html = `
    <div class="page-header"><h2>Dashboard</h2><p>${STATE.project.name}${STATE.project.contract_number ? ' &mdash; ' + STATE.project.contract_number : ''}</p></div>
    <div class="cards">
      <div class="card blue"><div class="label">Total Submittals</div><div class="value">${total}</div></div>
      <div class="card green"><div class="label">Approved / Closed</div><div class="value">${approved}</div><div class="sub">${pct}% complete</div></div>
      <div class="card yellow"><div class="label">Pending</div><div class="value">${pending}</div></div>
      <div class="card purple"><div class="label">In Review</div><div class="value">${inReview}</div></div>
      <div class="card orange"><div class="label">Action Required</div><div class="value">${action}</div></div>
      <div class="card red"><div class="label">Critical Path</div><div class="value">${critical}</div><div class="sub">Lead &ge; 8 weeks</div></div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px;">
      <div class="card">
        <div class="label" style="margin-bottom:12px;">Completion</div>
        <div style="text-align:center;">
          <div class="progress-ring">
            <svg width="80" height="80"><circle class="bg" cx="40" cy="40" r="35"/><circle class="fg" cx="40" cy="40" r="35" stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"/></svg>
            <div class="progress-pct">${pct}%</div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="label" style="margin-bottom:12px;">By Status</div>
        ${Object.entries(statusCounts).sort((a,b)=>b[1]-a[1]).map(([st,cnt]) => `
          <div class="chart-bar-row">
            <div class="chart-label">${st}</div>
            <div class="chart-bar" style="width:${Math.max(cnt/total*200,8)}px;background:${statusColors[st]||'#6b7280'}"><span>${cnt}</span></div>
          </div>`).join('')}
      </div>
    </div>

    <div class="card" style="margin-bottom:24px;">
      <div class="label" style="margin-bottom:12px;">By Division</div>
      ${Object.entries(divCounts).sort((a,b)=>a[0].localeCompare(b[0])).map(([div,cnt]) => `
        <div class="chart-bar-row">
          <div class="chart-label">${div}</div>
          <div class="chart-bar" style="width:${Math.max(cnt/total*300,8)}px;background:var(--accent)"><span>${cnt}</span></div>
        </div>`).join('')}
    </div>
  `;

  // Action items
  const actionItems = s.filter(x => ['Revise & Resubmit','Rejected'].includes(x.status));
  if (actionItems.length) {
    html += `<div class="table-wrap"><div class="table-toolbar" style="background:rgba(239,68,68,0.05);"><strong style="color:var(--orange);">&#9888; Action Required (${actionItems.length})</strong></div>
    <table><thead><tr><th>Number</th><th>Trade</th><th>Description</th><th>Status</th><th></th></tr></thead><tbody>
    ${actionItems.map(x => `<tr><td class="mono">${x.number}</td><td>${x.trade}</td><td>${x.description}</td><td>${statusBadge(x.status)}</td><td><button class="btn btn-sm" onclick="openEdit(${x.id})">Update</button></td></tr>`).join('')}
    </tbody></table></div>`;
  }

  return html;
}

// ── Register ──
function renderRegister() {
  const s = STATE.submittals;
  let html = `<div class="page-header"><h2>Submittal Register</h2><p>${s.length} submittals</p></div>`;
  html += `<div class="table-wrap">
    <div class="table-toolbar">
      <input type="text" id="regSearch" placeholder="Search descriptions, trades..." oninput="filterRegister()">
      <select id="regStatus" onchange="filterRegister()"><option value="">All Statuses</option>${['Not Started','In Preparation','Submitted','Under Review','Approved','Approved as Noted','Revise & Resubmit','Rejected','For Record Only','Closed'].map(st=>`<option>${st}</option>`).join('')}</select>
      <select id="regDiv" onchange="filterRegister()"><option value="">All Divisions</option>${[...new Set(s.map(x=>x.division))].sort().map(d=>`<option value="${d}">${d} - ${s.find(x=>x.division===d)?.division_name||''}</option>`).join('')}</select>
      <select id="regType" onchange="filterRegister()"><option value="">All Types</option>${['SD','PD','SS','CP','DI','MO','QC','CL','WP','SR'].map(t=>`<option value="${t}">${t} - ${typeLabel(t)}</option>`).join('')}</select>
    </div>
    <table><thead><tr>
      <th>Number</th><th>Spec</th><th>Division</th><th>Trade</th><th>Type</th><th>Description</th><th>Status</th><th>Lead</th><th></th>
    </tr></thead><tbody id="regBody">
    ${s.map(x => registerRow(x)).join('')}
    </tbody></table></div>`;
  return html;
}

function registerRow(x) {
  return `<tr data-id="${x.id}" data-status="${x.status}" data-div="${x.division}" data-type="${x.type_code}" data-search="${(x.description+' '+x.trade+' '+x.number).toLowerCase()}">
    <td class="mono">${x.number}</td><td class="mono">${x.spec_section}</td><td>${x.division}</td><td>${x.trade}</td>
    <td><span title="${typeLabel(x.type_code)}">${x.type_code}</span></td><td>${x.description}</td><td>${statusBadge(x.status)}</td>
    <td style="white-space:nowrap;">${leadIndicator(x.lead_time_weeks)}</td>
    <td><button class="btn btn-sm" onclick="openEdit(${x.id})">Edit</button></td></tr>`;
}

function filterRegister() {
  const search = (document.getElementById('regSearch')?.value || '').toLowerCase();
  const status = document.getElementById('regStatus')?.value || '';
  const div = document.getElementById('regDiv')?.value || '';
  const type = document.getElementById('regType')?.value || '';
  document.querySelectorAll('#regBody tr').forEach(tr => {
    let show = true;
    if (search && !tr.dataset.search.includes(search)) show = false;
    if (status && tr.dataset.status !== status) show = false;
    if (div && tr.dataset.div !== div) show = false;
    if (type && tr.dataset.type !== type) show = false;
    tr.style.display = show ? '' : 'none';
  });
}

// ── Critical Path ──
function renderCritical() {
  const critical = STATE.submittals
    .filter(x => x.lead_time_weeks >= 8 && !['Approved','Approved as Noted','Closed','For Record Only'].includes(x.status))
    .sort((a,b) => b.lead_time_weeks - a.lead_time_weeks);

  let html = `<div class="page-header"><h2>Critical Path Items</h2><p>Submittals with lead time &ge; 8 weeks that are not yet approved</p></div>`;

  if (!critical.length) {
    html += `<div class="card" style="text-align:center;padding:40px;"><p style="font-size:16px;">No critical path items — all long-lead submittals are approved.</p></div>`;
    return html;
  }

  html += `<div class="cards"><div class="card red"><div class="label">Critical Items</div><div class="value">${critical.length}</div></div>
    <div class="card orange"><div class="label">Longest Lead</div><div class="value">${critical[0]?.lead_time_weeks || 0}wk</div><div class="sub">${critical[0]?.description || ''}</div></div></div>`;

  html += `<div class="table-wrap"><table><thead><tr><th>Number</th><th>Lead</th><th>Status</th><th>Trade</th><th>Description</th><th>Division</th><th></th></tr></thead><tbody>
    ${critical.map(x => `<tr><td class="mono">${x.number}</td><td style="white-space:nowrap;">${leadIndicator(x.lead_time_weeks)}</td><td>${statusBadge(x.status)}</td>
    <td>${x.trade}</td><td>${x.description}</td><td>${x.division} - ${x.division_name}</td><td><button class="btn btn-sm" onclick="openEdit(${x.id})">Update</button></td></tr>`).join('')}
    </tbody></table></div>`;
  return html;
}

// ── Add Form ──
function renderAddForm() {
  const divOptions = STATE.csi ? Object.entries(STATE.csi.divisions).map(([code, div]) =>
    `<option value="${code}">${code} - ${div.name} (${div.trade})</option>`).join('') : '';

  return `<div class="page-header"><h2>Add Submittal</h2><p>Manually add a submittal to the register</p></div>
    <div class="setup-card" style="max-width:600px;margin:0;">
      <div class="form-row">
        <div class="form-group"><label>Division</label><select id="addDiv" onchange="updateTradeFromDiv()">${divOptions}</select></div>
        <div class="form-group"><label>Type</label><select id="addType">${['SD','PD','SS','CP','DI','MO','QC','CL','WP','SR'].map(t=>`<option value="${t}">${t} - ${typeLabel(t)}</option>`).join('')}</select></div>
      </div>
      <div class="form-group"><label>Description</label><input id="addDesc" placeholder="e.g., Structural Steel Shop Drawings"></div>
      <div class="form-row">
        <div class="form-group"><label>Spec Section</label><input id="addSpec" placeholder="e.g., 05 12 00"></div>
        <div class="form-group"><label>Trade</label><input id="addTrade" placeholder="e.g., Structural Steel"></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Lead Time (weeks)</label><input id="addLead" type="number" value="4" min="1" max="52"></div>
        <div class="form-group"><label>Date Required</label><input id="addDateReq" type="date"></div>
      </div>
      <div class="form-group"><label>Notes</label><textarea id="addNotes" rows="2"></textarea></div>
      <button class="btn btn-primary" onclick="addSubmittal()" style="margin-top:8px;">Add Submittal</button>
    </div>`;
}

function updateTradeFromDiv() {
  const div = document.getElementById('addDiv').value;
  if (STATE.csi && STATE.csi.divisions[div]) {
    document.getElementById('addTrade').value = STATE.csi.divisions[div].trade;
  }
}

async function addSubmittal() {
  const data = {
    division: document.getElementById('addDiv').value,
    type_code: document.getElementById('addType').value,
    description: document.getElementById('addDesc').value,
    spec_section: document.getElementById('addSpec').value,
    trade: document.getElementById('addTrade').value,
    lead_time_weeks: parseInt(document.getElementById('addLead').value) || 4,
    date_required: document.getElementById('addDateReq').value,
    notes: document.getElementById('addNotes').value,
  };
  if (!data.description) { alert('Description is required.'); return; }
  await api('POST', '/submittals', data);
  await loadState();
  toast('Submittal added');
  navigate('register');
}

// ── Generate ──
function renderGenerate() {
  if (!STATE.csi) return '<p>Loading CSI data...</p>';
  const divs = STATE.csi.divisions;
  return `<div class="page-header"><h2>Generate from CSI Reference</h2><p>Select divisions to auto-populate standard submittals with typical lead times</p></div>
    <div class="setup-card" style="max-width:700px;margin:0;">
      <div style="margin-bottom:12px;display:flex;gap:8px;">
        <button class="btn btn-sm" onclick="toggleAllDivs(true)">Select All</button>
        <button class="btn btn-sm" onclick="toggleAllDivs(false)">Deselect All</button>
      </div>
      <div class="division-grid">
        ${Object.entries(divs).map(([code, div]) => `
          <label class="div-check"><input type="checkbox" class="gen-div" value="${code}" checked> ${code} - ${div.name}</label>`).join('')}
      </div>
      <button class="btn btn-primary" onclick="generateSubmittals()">Generate Submittals</button>
    </div>`;
}

function toggleAllDivs(val) {
  document.querySelectorAll('.gen-div').forEach(cb => cb.checked = val);
}

async function generateSubmittals() {
  const divs = [...document.querySelectorAll('.gen-div:checked')].map(cb => cb.value);
  if (!divs.length) { alert('Select at least one division.'); return; }
  const res = await api('POST', '/generate', { divisions: divs });
  await loadState();
  toast(`Generated ${res.count} submittals`);
  navigate('dashboard');
}

// ── Scan Specs ──
function renderScan() {
  return `<div class="page-header"><h2>Scan Specifications</h2><p>Paste specification text to extract submittal requirements</p></div>
    <div class="setup-card" style="max-width:700px;margin:0;">
      <div class="form-group"><label>Specification Text</label>
        <textarea id="scanText" rows="15" placeholder="Paste your specification text here... The scanner will identify submittal requirements by looking for keywords like 'submit shop drawings', 'provide product data', 'furnish samples', etc."></textarea>
      </div>
      <button class="btn btn-primary" onclick="scanSpecs()">Scan for Submittals</button>
      <div id="scanResults" style="margin-top:16px;"></div>
    </div>`;
}

async function scanSpecs() {
  const text = document.getElementById('scanText').value;
  if (!text.trim()) { alert('Paste spec text first.'); return; }
  const res = await api('POST', '/scan', { text });
  const el = document.getElementById('scanResults');
  if (!res.items || !res.items.length) {
    el.innerHTML = '<p style="color:var(--yellow);">No submittal requirements detected. Try pasting a larger section of the spec.</p>';
    return;
  }
  el.innerHTML = `<p style="margin-bottom:12px;"><strong>${res.items.length} submittals found</strong></p>
    <table style="font-size:12px;"><thead><tr><th>Type</th><th>Division</th><th>Description</th><th>Lead</th></tr></thead><tbody>
    ${res.items.map(x => `<tr><td>${x.type_code}</td><td>${x.division||'—'}</td><td>${x.description}</td><td>${x.lead_time_weeks}wk</td></tr>`).join('')}
    </tbody></table>
    <button class="btn btn-success" onclick="importScan()" style="margin-top:12px;">Import All to Register</button>`;
  window._lastScanItems = res.items;
}

async function importScan() {
  if (!window._lastScanItems) return;
  const res = await api('POST', '/import-scan', { items: window._lastScanItems });
  await loadState();
  toast(`Imported ${res.count} submittals`);
  navigate('register');
}

// ── Settings ──
function renderSettings() {
  const p = STATE.project || {};
  return `<div class="setup-card">
    <h2>${STATE.project ? 'Project Settings' : 'Create Project'}</h2>
    <p>${STATE.project ? 'Update project details' : 'Set up your project to get started'}</p>
    <div class="form-group"><label>Project Name *</label><input id="setName" value="${p.name||''}"></div>
    <div class="form-row">
      <div class="form-group"><label>Contract Number</label><input id="setContract" value="${p.contract_number||''}"></div>
      <div class="form-group"><label>JOC Task Order</label><input id="setTaskOrder" value="${p.task_order||''}"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Owner / Agency</label><input id="setOwner" value="${p.owner||''}"></div>
      <div class="form-group"><label>A/E Firm</label><input id="setArchitect" value="${p.architect||''}"></div>
    </div>
    <div class="form-group"><label>General Contractor</label><input id="setContractor" value="${p.contractor||''}"></div>
    <button class="btn btn-primary" onclick="saveSettings()" style="margin-top:8px;">${STATE.project ? 'Save Settings' : 'Create Project'}</button>
  </div>`;
}

async function saveSettings() {
  const data = {
    name: document.getElementById('setName').value,
    contract_number: document.getElementById('setContract').value,
    task_order: document.getElementById('setTaskOrder').value,
    owner: document.getElementById('setOwner').value,
    architect: document.getElementById('setArchitect').value,
    contractor: document.getElementById('setContractor').value,
  };
  if (!data.name) { alert('Project name is required.'); return; }
  await api('POST', '/project', data);
  await loadState();
  toast('Project saved');
  navigate('dashboard');
}

// ── Edit Modal ──
function openEdit(id) {
  editingId = id;
  const sub = STATE.submittals.find(x => x.id === id);
  if (!sub) return;
  document.getElementById('editModalTitle').textContent = `Edit ${sub.number}: ${sub.description}`;
  document.getElementById('editModalBody').innerHTML = `
    <div class="form-row">
      <div class="form-group"><label>Status</label><select id="edStatus">${statusOptions(sub.status)}</select></div>
      <div class="form-group"><label>Lead Time (weeks)</label><input id="edLead" type="number" value="${sub.lead_time_weeks}" min="1" max="52"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Date Submitted</label><input id="edDateSub" type="date" value="${sub.date_submitted||''}"></div>
      <div class="form-group"><label>Date Returned</label><input id="edDateRet" type="date" value="${sub.date_returned||''}"></div>
    </div>
    <div class="form-group"><label>Date Required on Site</label><input id="edDateReq" type="date" value="${sub.date_required||''}"></div>
    <div class="form-group"><label>Notes</label><textarea id="edNotes" rows="3">${sub.notes||''}</textarea></div>`;
  document.getElementById('editModal').classList.add('open');
}

function closeModal() {
  document.getElementById('editModal').classList.remove('open');
  editingId = null;
}

async function saveEdit() {
  if (!editingId) return;
  const data = {
    id: editingId,
    status: document.getElementById('edStatus').value,
    lead_time_weeks: parseInt(document.getElementById('edLead').value),
    date_submitted: document.getElementById('edDateSub').value,
    date_returned: document.getElementById('edDateRet').value,
    date_required: document.getElementById('edDateReq').value,
    notes: document.getElementById('edNotes').value,
  };
  await api('PUT', '/submittals', data);
  await loadState();
  closeModal();
  toast('Submittal updated');
  render();
}

// ── Export ──
function exportCSV() {
  const s = STATE.submittals;
  if (!s.length) { toast('No submittals to export'); return; }
  const headers = ['Number','Spec Section','Division','Division Name','Trade','Type','Type Name','Description','Status','Lead Weeks','Date Required','Date Submitted','Date Returned','Disposition','Resubmittals','Notes'];
  const rows = s.map(x => [x.number,x.spec_section,x.division,x.division_name,x.trade,x.type_code,x.type_name,x.description,x.status,x.lead_time_weeks,x.date_required,x.date_submitted,x.date_returned,x.disposition,x.resubmittal_count,x.notes]);
  let csv = headers.join(',') + '\n' + rows.map(r => r.map(v => `"${String(v||'').replace(/"/g,'""')}"`).join(',')).join('\n');
  const blob = new Blob([csv], {type:'text/csv'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `submittal_register_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
  toast('CSV exported');
}

// ── Init ──
async function init() {
  await loadState();
  render();
}
init();
</script>
</body>
</html>'''


# ── HTTP Handler ───────────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress request logs

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def _html(self, content):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode())

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/" or path == "":
            self._html(get_html())
            return

        if path == "/api/state":
            db = load_db()
            project = get_active_project(db)
            csi = load_csi_data()
            submittals = project.get("submittals", []) if project else []
            self._json({
                "project": project.get("info") if project else None,
                "submittals": submittals,
                "csi": csi,
            })
            return

        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        if path == "/api/project":
            db = load_db()
            project = get_active_project(db)
            if project:
                project["info"].update(body)
            else:
                project = {
                    "id": len(db["projects"]) + 1,
                    "info": {**body, "created": datetime.now().isoformat()},
                    "submittals": [],
                    "next_id": 1,
                }
                db["projects"].append(project)
                db["active_project"] = project["id"]
            save_db(db)
            self._json({"ok": True})
            return

        if path == "/api/submittals":
            db = load_db()
            project = get_active_project(db)
            if not project:
                self._json({"error": "No project"}, 400)
                return
            csi = load_csi_data()
            div = body["division"].zfill(2)
            div_info = csi["divisions"].get(div, {})
            type_info = csi["submittal_types"].get(body["type_code"], {})
            sub_id = project.get("next_id", 1)
            number = next_submittal_number(project["submittals"], div)
            submittal = {
                "id": sub_id,
                "number": number,
                "spec_section": body.get("spec_section") or f"{div} 00 00",
                "division": div,
                "division_name": div_info.get("name", f"Division {div}"),
                "trade": body.get("trade") or div_info.get("trade", "TBD"),
                "description": body["description"],
                "type_code": body["type_code"],
                "type_name": type_info.get("name", ""),
                "status": "Not Started",
                "lead_time_weeks": body.get("lead_time_weeks", 4),
                "date_required": body.get("date_required", ""),
                "date_submitted": "",
                "date_returned": "",
                "disposition": "",
                "resubmittal_count": 0,
                "notes": body.get("notes", ""),
                "created": datetime.now().isoformat(),
                "updated": datetime.now().isoformat(),
            }
            project["submittals"].append(submittal)
            project["next_id"] = sub_id + 1
            save_db(db)
            self._json({"ok": True, "id": sub_id, "number": number})
            return

        if path == "/api/generate":
            db = load_db()
            project = get_active_project(db)
            if not project:
                self._json({"error": "No project"}, 400)
                return
            csi = load_csi_data()
            divisions = body.get("divisions", list(csi["divisions"].keys()))
            count = 0
            for div_code in divisions:
                if div_code not in csi["divisions"]:
                    continue
                div = csi["divisions"][div_code]
                for item in div["common_submittals"]:
                    sub_id = project.get("next_id", 1)
                    number = next_submittal_number(project["submittals"], div_code)
                    type_info = csi["submittal_types"].get(item["type"], {})
                    submittal = {
                        "id": sub_id,
                        "number": number,
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
                    project["submittals"].append(submittal)
                    project["next_id"] = sub_id + 1
                    count += 1
            save_db(db)
            self._json({"ok": True, "count": count})
            return

        if path == "/api/scan":
            csi = load_csi_data()
            text = body.get("text", "")
            items = scan_text(text, csi)
            self._json({"items": items})
            return

        if path == "/api/import-scan":
            db = load_db()
            project = get_active_project(db)
            if not project:
                self._json({"error": "No project"}, 400)
                return
            csi = load_csi_data()
            count = 0
            for item in body.get("items", []):
                sub_id = project.get("next_id", 1)
                div = item.get("division", "01").zfill(2)
                number = next_submittal_number(project["submittals"], div)
                type_info = csi["submittal_types"].get(item.get("type_code", "PD"), {})
                submittal = {
                    "id": sub_id,
                    "number": number,
                    "spec_section": item.get("spec_section", ""),
                    "division": div,
                    "division_name": item.get("division_name", ""),
                    "trade": item.get("trade", "TBD"),
                    "description": item["description"],
                    "type_code": item.get("type_code", "PD"),
                    "type_name": type_info.get("name", ""),
                    "status": "Not Started",
                    "lead_time_weeks": item.get("lead_time_weeks", 4),
                    "date_required": "",
                    "date_submitted": "",
                    "date_returned": "",
                    "disposition": "",
                    "resubmittal_count": 0,
                    "notes": "Imported from spec scan",
                    "created": datetime.now().isoformat(),
                    "updated": datetime.now().isoformat(),
                }
                project["submittals"].append(submittal)
                project["next_id"] = sub_id + 1
                count += 1
            save_db(db)
            self._json({"ok": True, "count": count})
            return

        self.send_error(404)

    def do_PUT(self):
        path = urlparse(self.path).path
        body = self._read_body()

        if path == "/api/submittals":
            db = load_db()
            project = get_active_project(db)
            if not project:
                self._json({"error": "No project"}, 400)
                return
            target = None
            for s in project["submittals"]:
                if s["id"] == body.get("id"):
                    target = s
                    break
            if not target:
                self._json({"error": "Not found"}, 404)
                return

            if "status" in body:
                old_status = target["status"]
                target["status"] = body["status"]
                target["disposition"] = body["status"]
                if body["status"] == "Revise & Resubmit" and old_status != "Revise & Resubmit":
                    target["resubmittal_count"] = target.get("resubmittal_count", 0) + 1
            if "lead_time_weeks" in body:
                target["lead_time_weeks"] = body["lead_time_weeks"]
            if "date_submitted" in body:
                target["date_submitted"] = body["date_submitted"]
            if "date_returned" in body:
                target["date_returned"] = body["date_returned"]
            if "date_required" in body:
                target["date_required"] = body["date_required"]
            if "notes" in body:
                target["notes"] = body["notes"]
            target["updated"] = datetime.now().isoformat()
            save_db(db)
            self._json({"ok": True})
            return

        self.send_error(404)


def scan_text(text, csi):
    """Scan specification text for submittal requirements."""
    import re
    items = []
    lines = text.split("\n")
    current_section = ""
    current_division = ""
    in_submittal_section = False

    for line in lines:
        sec_match = re.match(r"(?i)(?:SECTION\s+)?(\d{2})\s*(\d{2})\s*(\d{2})", line)
        if sec_match:
            current_section = f"{sec_match.group(1)} {sec_match.group(2)} {sec_match.group(3)}"
            current_division = sec_match.group(1)

        if re.search(r"(?i)SUBMITTALS|SUBMITTAL\s+REQUIREMENTS", line):
            in_submittal_section = True
            continue

        if in_submittal_section and re.match(r"(?i)\s*(PART\s+[23]|^\d+\.\d+\s+(?!SUBMITTALS))", line):
            in_submittal_section = False

        if in_submittal_section or re.search(r"(?i)(submit|furnish|provide)\s+(the\s+following\s+)?(shop|product|sample|certif|test|mix|warrant|mock|manua|as.built|closeout|design|work\s+plan|safety)", line):
            for pattern, type_code in [
                (r"(?i)shop\s+drawings?", "SD"), (r"(?i)product\s+data", "PD"),
                (r"(?i)samples?", "SS"), (r"(?i)certificates?", "CP"),
                (r"(?i)test\s+reports?", "QC"), (r"(?i)mix\s+designs?", "DI"),
                (r"(?i)mock.?ups?", "MO"), (r"(?i)o\s*&\s*m\s+manuals?", "CL"),
                (r"(?i)warran(?:ty|tee|ties)", "CL"), (r"(?i)as.?built", "CL"),
                (r"(?i)work\s+plan|method\s+statement", "WP"),
                (r"(?i)safety\s+plan|HASP", "WP"), (r"(?i)design\s+(?:data|calc)", "DI"),
            ]:
                if re.search(pattern, line):
                    desc = line.strip()
                    desc = re.sub(r"^[A-Z]\.\s*", "", desc)
                    desc = re.sub(r"^\d+\.\s*", "", desc)
                    desc = re.sub(r"^[-•]\s*", "", desc)
                    desc = desc.strip()
                    if len(desc) > 10:
                        div = current_division or "01"
                        div_info = csi["divisions"].get(div, {})
                        lead = 4
                        for ref in div_info.get("common_submittals", []):
                            if ref["type"] == type_code:
                                lead = ref["lead_weeks"]
                                break
                        items.append({
                            "description": desc[:120],
                            "type_code": type_code,
                            "spec_section": current_section,
                            "division": div,
                            "division_name": div_info.get("name", f"Division {div}"),
                            "trade": div_info.get("trade", "TBD"),
                            "lead_time_weeks": lead,
                        })
                    break
    return items


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Construction Submittal Tracker Web App")
    parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    # Ensure data dir exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    handler = Handler
    with socketserver.TCPServer((args.host, args.port), handler) as httpd:
        httpd.allow_reuse_address = True
        url = f"http://localhost:{args.port}"
        print(f"\n  Construction Submittal Tracker")
        print(f"  {'=' * 40}")
        print(f"  Running at: {url}")
        print(f"  Data dir:   {DATA_DIR}")
        print(f"  Press Ctrl+C to stop\n")

        if not args.no_browser:
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Shutting down...")
            httpd.shutdown()


if __name__ == "__main__":
    main()
