#!/usr/bin/env node
/**
 * NTXP Project Init offer hook.
 *
 *   node ntxp-project-init-hook.cjs prompt    UserPromptSubmit: offer on new-project intent
 *   node ntxp-project-init-hook.cjs reset     Clear offer/decline state
 *
 * This hook only prints an instruction into Claude's context. It never creates
 * anything. The skill itself asks the user before doing any work.
 */
const fs = require('fs');
const path = require('path');

const ROOT = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const STATE = path.join(ROOT, '.claude-flow', 'data', 'ntxp-init-state.json');
const COOLDOWN_MS = 30 * 60 * 1000;
const DECLINE_MS = 12 * 60 * 60 * 1000;

const INTENT = new RegExp(
  [
    'new (ntxp )?project',
    'new bid',
    'kick ?off (a |the |our )?(new )?(project|bid)',
    'got (the )?award',
    'we (were|got) awarded',
    'awarded (the )?(project|contract)',
    'set ?up (a |the )?new (project|bid)',
    'project init',
    'ntxp-\\d{4}-\\d+',
  ].join('|'),
  'i'
);

const OFFER = [
  '[NTXP Project Init] This may be a new construction project or bid. Ignore this notice if the',
  'message is about software (a code project, repo, or background job). Do NOT start setup yet.',
  'Ask the user with AskUserQuestion whether they want to start a new NTXP project now.',
  'If yes, use the "ntxp-project-init" skill. It asks first, then calls the skills that own each step:',
  '  0 environment preflight   1 NTXP ID   2 IPDM authority   3 register in ntxp-projects',
  '  4 Drive folders (ntxp-folder-structure v1.2)   5 Project Coda   6 models and executors',
  '  7 Claude Flow (dev only)   8 verify   9 share back',
  'If the user declines, the skill records it and the offer stays quiet for 12 hours.',
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
function suppressed(state, key) {
  if (state.declined) {
    var at = state.declinedAt;
    if (!at) { try { at = fs.statSync(STATE).mtimeMs; } catch (e) { at = 0; } }
    if (Date.now() - at < DECLINE_MS) return true;
    delete state.declined;
    delete state.declinedAt;
  }
  return state[key] && Date.now() - state[key] < COOLDOWN_MS;
}

const mode = process.argv[2];
const state = readState();

if (mode === 'prompt') {
  const input = readStdin();
  const prompt = String(input.prompt || '');
  if (INTENT.test(prompt) && !/ntxp project init/i.test(prompt) && !suppressed(state, 'promptOfferedAt')) {
    state.promptOfferedAt = Date.now();
    writeState(state);
    console.log(OFFER);
  }
} else if (mode === 'reset') {
  writeState({});
  console.log('[NTXP Project Init] state reset');
} else {
  console.error('usage: ntxp-project-init-hook.cjs prompt|reset');
  process.exit(1);
}
