// NTXP Master Contracts — dashboard.
// Inline-editable contract log: click a cell, type, it saves instantly. No
// popups, no dialogs. Concurrent editors are safe because every save is a
// single-field PATCH (different cells never collide) carrying the row revision
// for optimistic locking; the page polls for other people's saves and merges
// them in without disturbing the cell you're in.

const $ = (s, r = document) => r.querySelector(s);
const rowsEl = $('#rows'), emptyEl = $('#empty'), flashEl = $('#flash');
let META = { contract_types: [], scope_vocab: [], poll_ms: 4000 };
let CONTRACTS = [];
let latestSeq = 0;
let editingId = null;     // contract id with a focused cell — pause live merges

const actorInput = $('#actor');
actorInput.value = localStorage.getItem('ntxp_actor') || '';
actorInput.addEventListener('input', () => localStorage.setItem('ntxp_actor', actorInput.value));
const actor = () => actorInput.value.trim() || 'web';

const fmtMoney = v => v == null || v === '' ? '' :
  '$' + Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 });
const esc = s => (s ?? '').toString().replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function flash(msg, color) {
  flashEl.textContent = msg || 'saved ✓';
  flashEl.style.color = color || 'var(--success)';
  flashEl.classList.add('show');
  clearTimeout(flash._t);
  flash._t = setTimeout(() => flashEl.classList.remove('show'), 1400);
}

function daysTo(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr + 'T00:00:00');
  if (isNaN(d)) return null;
  return Math.round((d - new Date(new Date().toDateString())) / 86400000);
}

// --- saving --------------------------------------------------------------
async function save(c, field, value, cellEl) {
  try {
    const res = await fetch('/api/contracts/' + c.contract_id, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ field, value, rev: c.rev, actor: actor() })
    });
    const data = await res.json();
    if (res.status === 409) {
      // someone saved this row first — adopt the fresh row, reflect this cell
      mergeContract(data.contract);
      flash('refreshed (teammate edited)', 'var(--warning)');
      return data.contract;
    }
    if (!res.ok) { flash(data.error || 'error', 'var(--danger)'); return null; }
    mergeContract(data.contract);
    flash();
    return data.contract;
  } catch (e) { flash('offline', 'var(--danger)'); return null; }
}

function mergeContract(updated) {
  const i = CONTRACTS.findIndex(x => x.contract_id === updated.contract_id);
  if (i >= 0) CONTRACTS[i] = updated; else CONTRACTS.push(updated);
}

// --- cell builders -------------------------------------------------------
function textCell(c, field, opts = {}) {
  const inp = document.createElement('input');
  inp.className = 'cell';
  inp.value = c[field] ?? '';
  if (opts.placeholder) inp.placeholder = opts.placeholder;
  inp.addEventListener('focus', () => editingId = c.contract_id);
  inp.addEventListener('blur', async () => {
    editingId = null;
    if ((inp.value ?? '') !== (c[field] ?? ''))
      await save(c, field, inp.value, inp);
  });
  inp.addEventListener('keydown', e => { if (e.key === 'Enter') inp.blur(); });
  return inp;
}

function numCell(c, field, opts = {}) {
  const inp = textCell(c, field, opts);
  inp.style.maxWidth = opts.width || '110px';
  return inp;
}

function dateCell(c, field) {
  const inp = document.createElement('input');
  inp.type = 'date'; inp.className = 'cell'; inp.style.maxWidth = '150px';
  inp.value = c[field] || '';
  inp.addEventListener('focus', () => editingId = c.contract_id);
  inp.addEventListener('change', async () => { await save(c, field, inp.value); });
  inp.addEventListener('blur', () => editingId = null);
  return inp;
}

function selectCell(c, field, options, opts = {}) {
  const sel = document.createElement('select');
  sel.className = 'cell';
  const blank = document.createElement('option');
  blank.value = ''; blank.textContent = opts.blank || '—'; sel.appendChild(blank);
  options.forEach(o => {
    const op = document.createElement('option');
    op.value = o; op.textContent = o;
    if ((c[field] || '') === o) op.selected = true;
    sel.appendChild(op);
  });
  sel.addEventListener('focus', () => editingId = c.contract_id);
  sel.addEventListener('change', async () => { await save(c, field, sel.value); });
  sel.addEventListener('blur', () => editingId = null);
  return sel;
}

function flagCell(c) {
  const span = document.createElement('span');
  const set = () => {
    span.className = 'flag ' + (c.is_executed ? 'exec' : 'unexec');
    span.innerHTML = `<span class="dot"></span>${c.is_executed ? 'Executed' : 'Unexecuted'}`;
    span.title = c.is_executed ? 'Click to flag as unexecuted'
      : 'Unexecuted — click when the signed copy is in';
  };
  set();
  span.addEventListener('click', async () => {
    const updated = await save(c, 'is_executed', !c.is_executed);
    if (updated) { c.is_executed = updated.is_executed; set(); }
  });
  return span;
}

function pdfCell(c) {
  const wrap = document.createElement('span');
  const render = () => {
    wrap.innerHTML = '';
    if (c.pdf_url) {
      const a = document.createElement('a');
      a.href = c.pdf_url; a.target = '_blank'; a.className = 'pdf-yes';
      a.textContent = '📄 view';
      wrap.appendChild(a);
    }
    const pencil = document.createElement('span');
    pencil.className = 'pencil'; pencil.textContent = c.pdf_url ? ' ✎' : '＋ link';
    pencil.title = 'Paste the live link to the signed PDF';
    pencil.onclick = () => {
      const inp = document.createElement('input');
      inp.className = 'cell'; inp.value = c.pdf_url || '';
      inp.placeholder = 'https://…/signed.pdf'; inp.style.minWidth = '160px';
      wrap.innerHTML = ''; wrap.appendChild(inp); inp.focus();
      editingId = c.contract_id;
      inp.addEventListener('blur', async () => {
        editingId = null;
        if ((inp.value || '') !== (c.pdf_url || '')) {
          const u = await save(c, 'pdf_url', inp.value);
          if (u) c.pdf_url = u.pdf_url;
        }
        render();
      });
      inp.addEventListener('keydown', e => { if (e.key === 'Enter') inp.blur(); });
    };
    wrap.appendChild(pencil);
  };
  render();
  return wrap;
}

function conoCell(c) {
  const wrap = document.createElement('div');
  wrap.className = 'cono';
  const a = document.createElement('a');
  a.href = '/contract?id=' + c.contract_id;
  a.textContent = c.contract_no || '(no #)';
  a.title = 'Open contract profile';
  wrap.appendChild(a);
  const pencil = document.createElement('span');
  pencil.className = 'pencil'; pencil.textContent = '✎';
  pencil.title = 'Edit number';
  pencil.onclick = () => {
    const inp = textCell(c, 'contract_no', { placeholder: 'contract / RFP #' });
    inp.style.maxWidth = '130px';
    wrap.innerHTML = ''; wrap.appendChild(inp); inp.focus();
    inp.addEventListener('blur', () => renderRows()); // re-render to restore link
  };
  wrap.appendChild(pencil);
  return wrap;
}

function td(child, cls) {
  const cell = document.createElement('td');
  if (cls) cell.className = cls;
  if (child instanceof Node) cell.appendChild(child); else cell.innerHTML = child;
  return cell;
}

// --- render --------------------------------------------------------------
function renderRows() {
  const q = ($('#search').value || '').toLowerCase().trim();
  const list = CONTRACTS.filter(c => !q ||
    [c.contract_title, c.contract_no, c.owner_entity, c.location, c.allowable_scope]
      .some(v => (v || '').toLowerCase().includes(q)));
  rowsEl.innerHTML = '';
  emptyEl.style.display = list.length ? 'none' : 'block';

  for (const c of list) {
    const tr = document.createElement('tr');
    const d = daysTo(c.expiration_date);
    if (d != null && d < 0) tr.className = 'expired';
    else if (d != null && d <= 90) tr.className = 'soon';

    tr.appendChild(td(conoCell(c), 'num'));
    tr.appendChild(td(textCell(c, 'contract_title', { placeholder: 'Contract title' })));
    tr.appendChild(td(selectCell(c, 'contract_type', META.contract_types, { blank: 'Type' })));
    tr.appendChild(td(textCell(c, 'owner_entity', { placeholder: 'Owner entity' })));
    tr.appendChild(td(numCell(c, 'coefficient_multiplier', { placeholder: '1.00', width: '90px' }), 'num'));
    tr.appendChild(td(numCell(c, 'cooperative_fee', { placeholder: '0%', width: '90px' }), 'num'));

    const expWrap = document.createElement('span');
    expWrap.className = 'exp ' + (d != null && d < 0 ? 'exp-expired' : d != null && d <= 90 ? 'exp-soon' : '');
    expWrap.appendChild(dateCell(c, 'expiration_date'));
    tr.appendChild(td(expWrap, 'num'));

    tr.appendChild(td(textCell(c, 'allowable_scope', { placeholder: 'electrical, GC…' })));
    tr.appendChild(td(pdfCell(c)));
    tr.appendChild(td(flagCell(c)));

    const tools = document.createElement('div');
    tools.className = 'rowtools';
    const del = document.createElement('button');
    del.className = 'iconbtn'; del.textContent = '🗑'; del.title = 'Remove';
    let armed = false;
    del.onclick = async () => {
      if (!armed) { armed = true; del.textContent = '✓?'; del.title = 'Click again to remove';
        setTimeout(() => { armed = false; del.textContent = '🗑'; }, 2500); return; }
      await fetch('/api/contracts/' + c.contract_id, { method: 'DELETE' });
      CONTRACTS = CONTRACTS.filter(x => x.contract_id !== c.contract_id);
      renderRows(); flash('removed');
    };
    tools.appendChild(del);
    tr.appendChild(td(tools, 'no-print'));
    rowsEl.appendChild(tr);
  }
  $('#printmeta').textContent =
    `${list.length} contracts · generated ${new Date().toLocaleDateString()}`;
}

// --- data load + live polling -------------------------------------------
async function loadAll() {
  META = await (await fetch('/api/meta')).json();
  const data = await (await fetch('/api/contracts')).json();
  CONTRACTS = data.contracts; latestSeq = data.latest_seq;
  renderRows();
}

async function poll() {
  try {
    const ch = await (await fetch('/api/changes?since=' + latestSeq)).json();
    if (ch.changed && editingId == null) {
      const data = await (await fetch('/api/contracts')).json();
      CONTRACTS = data.contracts; latestSeq = ch.latest_seq;
      renderRows();
    } else if (ch.changed) {
      latestSeq = ch.latest_seq; // defer re-render until the editor blurs
    }
  } catch (e) { /* transient */ }
  setTimeout(poll, META.poll_ms || 4000);
}

// --- toolbar -------------------------------------------------------------
$('#search').addEventListener('input', renderRows);
$('#add').addEventListener('click', async () => {
  const res = await fetch('/api/contracts', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ actor: actor() })
  });
  const { contract } = await res.json();
  CONTRACTS.unshift(contract); renderRows(); flash('added');
  // focus the title of the new row
  const firstTitle = rowsEl.querySelector('tr td:nth-child(2) input');
  if (firstTitle) firstTitle.focus();
});
$('#printBtn').addEventListener('click', () => window.print());
$('#pdfBtn').addEventListener('click', () => window.print()); // choose "Save as PDF"

loadAll().then(poll);
