#!/usr/bin/env node
/**
 * NTXP Project Init offer hook.
 *
 *   node ntxp-project-init-hook.cjs prompt          UserPromptSubmit: offer on new-project intent
 *   node ntxp-project-init-hook.cjs decline [dir]   Record a decline for a project directory (12 hours)
 *   node ntxp-project-init-hook.cjs reset [dir]     Clear offer/decline state for a project directory
 *
 * This hook only prints an instruction into Claude's context. It never creates
 * anything in the project. The skill itself asks the user before doing any work.
 */
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');

const COOLDOWN_MS = 30 * 60 * 1000;
const DECLINE_MS = 12 * 60 * 60 * 1000;
// Per-user state outside any repository, so offers never dirty a worktree.
const STATE_DIR = path.join(process.env.XDG_STATE_HOME || path.join(os.homedir(), '.local', 'state'), 'ntxp-project-init');

function projectRoot(dir) {
  return dir || process.env.CLAUDE_PROJECT_DIR || process.cwd();
}
// Hash of the canonical path: distinct directories never share a state file.
function statePath(root) {
  let real = root;
  try { real = fs.realpathSync(root); } catch (e) { /* keep as given */ }
  return path.join(STATE_DIR, crypto.createHash('sha256').update(real).digest('hex').slice(0, 16) + '.json');
}
function readState(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) { return {}; }
}
function writeState(file, s) {
  try {
    fs.mkdirSync(STATE_DIR, { recursive: true });
    fs.writeFileSync(file, JSON.stringify(s, null, 2));
  } catch (e) { /* non-fatal */ }
}
function readStdin() {
  try {
    const raw = fs.readFileSync(0, 'utf8');
    try { return JSON.parse(raw); } catch (e) { return { prompt: raw }; }
  } catch (e) { return {}; }
}
function shq(s) { return "'" + String(s).replace(/'/g, "'\\''") + "'"; }

const INTENT = new RegExp(
  '\\b(?:' + [
    'new (ntxp )?project',
    'new bid',
    'kick ?off (a |the |our )?(new )?(project|bid)',
    'got (the )?award',
    'we (were|got) awarded',
    'awarded (the )?(project|contract)',
    'set ?up (a |the )?new (project|bid)',
    'project init',
  ].join('|') + ')\\b',
  'i'
);
// A software request ("set up a new project in React") must not trigger an offer or use up the cooldown.
const SOFTWARE = /\b(react|vue|angular|svelte|next\.?js|node(\.?js)?|npm|yarn|pnpm|python|typescript|javascript|rust|golang|java|docker|kubernetes|repo|repository|git|github|api|database|sql|function|component|library|framework|package|cli|script|app|website|frontend|backend)\b/i;
// Only unambiguous construction terms override the software check: "building", "contract", "owner" and "school" are common in software requests too.
const CONSTRUCTION = /\b(bid|bids|award|awarded|jobtread|rfp|joc|isd|subcontract\w*|renovation|architect|takeoff)\b/i;

function suppressed(state, key, file) {
  if (state.declined) {
    let at = state.declinedAt;
    if (!at) { try { at = fs.statSync(file).mtimeMs; } catch (e) { at = 0; } }
    if (Date.now() - at < DECLINE_MS) return true;
    delete state.declined;
    delete state.declinedAt;
  }
  return Boolean(state[key]) && Date.now() - state[key] < COOLDOWN_MS;
}

function offerText(root) {
  const declineCmd = 'node ' + shq(__filename) + ' decline ' + shq(root);
  return [
    '[NTXP Project Init] This may be a new construction project or bid. Ignore this notice if the',
    'message is about software (a code project, repo, or background job). Do NOT start setup yet.',
    'Ask the user with AskUserQuestion whether they want to start a new NTXP project now.',
    'If yes, use the "ntxp-project-init" skill. It asks first, then calls the skills that own each step:',
    '  0 environment preflight   1 NTXP ID   2 IPDM authority   3 register in ntxp-projects',
    '  4 Drive folders (ntxp-folder-structure v1.2)   5 Project Coda   6 models and executors',
    '  7 Claude Flow (dev only)   8 verify   9 share back',
    'If the user declines, run exactly this to keep the offer quiet for 12 hours:',
    '  ' + declineCmd,
  ].join('\n');
}

const mode = process.argv[2];

if (mode === 'prompt') {
  const root = projectRoot();
  const file = statePath(root);
  const state = readState(file);
  const prompt = String(readStdin().prompt || '');
  const intent = INTENT.test(prompt) && !/ntxp project init/i.test(prompt);
  const software = SOFTWARE.test(prompt) && !CONSTRUCTION.test(prompt);
  if (intent && !software && !suppressed(state, 'promptOfferedAt', file)) {
    state.promptOfferedAt = Date.now();
    writeState(file, state);
    console.log(offerText(root));
  }
} else if (mode === 'decline') {
  const file = statePath(projectRoot(process.argv[3]));
  const state = readState(file);
  state.declined = true;
  state.declinedAt = Date.now();
  writeState(file, state);
  console.log('[NTXP Project Init] decline recorded for 12 hours');
} else if (mode === 'reset') {
  writeState(statePath(projectRoot(process.argv[3])), {});
  console.log('[NTXP Project Init] state reset');
} else {
  console.error('usage: ntxp-project-init-hook.cjs prompt|decline [dir]|reset [dir]');
  process.exit(1);
}
