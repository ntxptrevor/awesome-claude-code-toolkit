#!/usr/bin/env node
/**
 * NTXP Project Init offer hook.
 *
 *   node ntxp-project-init-hook.cjs prompt    UserPromptSubmit: offer on new-project intent
 *   node ntxp-project-init-hook.cjs session   SessionStart: offer when no project record exists
 *   node ntxp-project-init-hook.cjs reset     Clear offer/decline state
 *
 * This hook only prints an instruction into Claude's context. It never creates
 * anything. The skill itself asks the user before doing any work.
 */
const fs = require('fs');
const path = require('path');

const ROOT = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const STATE = path.join(ROOT, '.claude-flow', 'data', 'ntxp-init-state.json');
const PROJECT = path.join(ROOT, '.ntxp', 'ipdm', 'project.yaml');
const COOLDOWN_MS = 30 * 60 * 1000;

const INTENT = new RegExp(
  [
    'new (ntxp )?project',
    'new bid',
    'kick ?off',
    'got (the )?award',
    'we (were|got) awarded',
    'awarded (the )?(project|contract|job)',
    'set ?up (a |the )?(new )?(project|bid|job)',
    'start(ing)? (a |the )?(new )?(project|bid|job)',
    'project init',
    'ntxp-\\d{4}-\\d+',
  ].join('|'),
  'i'
);

const OFFER = [
  '[NTXP Project Init] This looks like a new project. Do NOT start setup yet.',
  'Ask the user with AskUserQuestion whether they want to create a new NTXP project now.',
  'If yes, use the "NTXP Project Init" skill and collect: project name, client/owner, contract type,',
  'cooperative, status. Workflow steps it will run (user can deselect any):',
  '  1 Claude Flow core   2 NTXP ID auth   3 IPDM project record   4 Drive folders 1-13 + !Public Share',
  '  5 Project Coda registry + crosswalk   6 Knowledge-base wiring   7 Model Council + Highway routing',
  '  8 Verify   9 Commit/push (separate confirmation)   10 Report',
  'If the user declines, do not ask again this session.',
].join('\n');

function readState() {
  try { return JSON.parse(fs.readFileSync(STATE, 'utf8')); } catch { return {}; }
}
function writeState(s) {
  try {
    fs.mkdirSync(path.dirname(STATE), { recursive: true });
    fs.writeFileSync(STATE, JSON.stringify(s, null, 2));
  } catch { /* non-fatal */ }
}
function readStdin() {
  try {
    const raw = fs.readFileSync(0, 'utf8');
    try { return JSON.parse(raw); } catch { return { prompt: raw }; }
  } catch { return {}; }
}
function hasProject() {
  try {
    const y = fs.readFileSync(PROJECT, 'utf8');
    const m = y.match(/^\s*id:\s*"?([^"\n]*)"?\s*$/m);
    return !!(m && m[1].trim());
  } catch { return false; }
}
function suppressed(state) {
  if (state.declined) return true;
  return state.offeredAt && Date.now() - state.offeredAt < COOLDOWN_MS;
}

const mode = process.argv[2];
const state = readState();

if (mode === 'prompt') {
  const input = readStdin();
  const prompt = String(input.prompt || '');
  if (INTENT.test(prompt) && !/ntxp project init/i.test(prompt) && !suppressed(state)) {
    state.offeredAt = Date.now();
    writeState(state);
    console.log(OFFER);
  }
} else if (mode === 'session') {
  readStdin();
  delete state.declined;
  if (!hasProject() && !suppressed(state)) {
    state.offeredAt = Date.now();
    writeState(state);
    console.log(
      '[NTXP Project Init] No project record found (.ntxp/ipdm/project.yaml). ' +
      'If the user starts on a new project, offer the "NTXP Project Init" skill; do not run it unasked.'
    );
  }
} else if (mode === 'reset') {
  writeState({});
  console.log('[NTXP Project Init] state reset');
} else {
  console.error('usage: ntxp-project-init-hook.cjs prompt|session|reset');
  process.exit(1);
}
