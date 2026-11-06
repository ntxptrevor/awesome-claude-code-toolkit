#!/usr/bin/env node
/**
 * MCP Connection Watchdog
 *
 * Detects dropped MCP server connections and attempts repair.
 * Runs as a hook on UserPromptSubmit (scan for failures) and
 * PreToolUse (intercept calls to dead servers).
 *
 * Usage:
 *   node mcp-watchdog.cjs scan          # Scan stdin for connection failures
 *   node mcp-watchdog.cjs check <tool>  # Check if a tool's server is alive
 *   node mcp-watchdog.cjs repair        # Attempt to repair known failures
 *   node mcp-watchdog.cjs status        # Print current watchdog state
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const PROJECT_DIR = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const STATE_FILE = path.join(PROJECT_DIR, '.claude-flow', 'data', 'mcp-watchdog-state.json');
const LOG_FILE = path.join(PROJECT_DIR, '.claude-flow', 'logs', 'mcp-watchdog.log');

// Known MCP server patterns and their repair strategies
const SERVER_REGISTRY = {
  'claude-flow': {
    type: 'local-npx',
    command: 'npx -y @claude-flow/cli@latest mcp start',
    repair: 'restart',
    critical: false,
  },
  'hostinger': {
    type: 'remote-api',
    pattern: /hostinger|hpanel/i,
    repair: 'reconnect',
    critical: false,
    knownIssues: ['CONNECTION_CLOSED', 'CONNECT_TIMEOUT', '403', '404'],
  },
  'github': {
    type: 'managed',
    pattern: /mcp__github__/,
    repair: 'wait-and-retry',
    critical: true,
  },
};

// Failure patterns to detect in system reminders
const FAILURE_PATTERNS = [
  { regex: /(\S+)\s*\(CONNECTION_CLOSED\):\s*"(.+?)"/g, type: 'CONNECTION_CLOSED' },
  { regex: /(\S+)\s*\(CONNECT_TIMEOUT\):\s*"(.+?)"/g, type: 'CONNECT_TIMEOUT' },
  { regex: /(\S+)\s*\(404\):\s*"(.+?)"/g, type: '404' },
  { regex: /(\S+)\s*\(403\):\s*"(.+?)"/g, type: '403' },
  { regex: /(\S+)\s*\(502\):\s*"(.+?)"/g, type: '502' },
  { regex: /(\S+)\s*\(503\):\s*"(.+?)"/g, type: '503' },
  { regex: /failed to connect.*?tools.*?mcp__(\S+?)__/gi, type: 'GENERIC_FAIL' },
];

// ============================================================
// State management
// ============================================================

function loadState() {
  try {
    if (fs.existsSync(STATE_FILE)) {
      return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
    }
  } catch {}
  return {
    failures: {},       // serverId -> { type, count, firstSeen, lastSeen, repairAttempts }
    repairs: {},        // serverId -> { lastAttempt, result, strategy }
    healthy: [],        // serverIds last confirmed healthy
    sessionStart: new Date().toISOString(),
  };
}

function saveState(state) {
  try {
    const dir = path.dirname(STATE_FILE);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
  } catch {}
}

function log(msg) {
  try {
    const dir = path.dirname(LOG_FILE);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    const line = `[${new Date().toISOString()}] ${msg}\n`;
    fs.appendFileSync(LOG_FILE, line);
  } catch {}
}

// ============================================================
// Scan: parse stdin for MCP connection failure notices
// ============================================================

function scanForFailures(input) {
  const state = loadState();
  let foundAny = false;

  for (const pattern of FAILURE_PATTERNS) {
    let match;
    const regex = new RegExp(pattern.regex.source, pattern.regex.flags);
    while ((match = regex.exec(input)) !== null) {
      const serverId = match[1].replace(/['"]/g, '').trim();
      const errorMsg = match[2] || '';

      // Skip auth-required servers (those need manual OAuth, not repair)
      if (/require.+authentication/i.test(input.substring(Math.max(0, match.index - 200), match.index + 200))) {
        continue;
      }

      if (!state.failures[serverId]) {
        state.failures[serverId] = {
          type: pattern.type,
          count: 0,
          firstSeen: new Date().toISOString(),
          lastSeen: null,
          repairAttempts: 0,
          errorMsg: '',
        };
      }

      const f = state.failures[serverId];
      f.count++;
      f.lastSeen = new Date().toISOString();
      f.type = pattern.type;
      f.errorMsg = errorMsg.substring(0, 200);
      foundAny = true;

      log(`DETECTED: ${serverId} — ${pattern.type}: ${errorMsg.substring(0, 100)}`);
    }
  }

  // Also scan for "still connecting" servers — these aren't failures yet
  const connectingMatch = input.match(/still connecting.*?:\n([\s\S]*?)(?:\n\n|If the user)/);
  if (connectingMatch) {
    const connecting = connectingMatch[1].split('\n').map(l => l.trim()).filter(Boolean);
    state.connecting = connecting;
  }

  // Scan for servers that ARE working (remove from failures)
  const healthyMatch = input.match(/tools.*?are.*?available/gi);
  if (healthyMatch) {
    // If we see tools becoming available, mark their servers healthy
    for (const serverId of Object.keys(state.failures)) {
      // Check if this server's tools are now mentioned as available
      if (input.includes(`mcp__${serverId}__`) && !input.includes(`${serverId} (CONNECTION_CLOSED)`) && !input.includes(`${serverId} (CONNECT_TIMEOUT)`)) {
        delete state.failures[serverId];
        if (!state.healthy.includes(serverId)) state.healthy.push(serverId);
        log(`HEALED: ${serverId} — tools available again`);
      }
    }
  }

  saveState(state);
  return { foundAny, state };
}

// ============================================================
// Check: is a specific tool's server alive?
// ============================================================

function checkTool(toolName) {
  const state = loadState();

  // Extract server ID from tool name (mcp__serverId__toolName)
  const parts = toolName.match(/^mcp__(.+?)__/);
  if (!parts) return { alive: true, serverId: null };

  const serverId = parts[1];
  const failure = state.failures[serverId];

  if (failure && failure.count > 0) {
    const minutesSinceLastSeen = (Date.now() - new Date(failure.lastSeen).getTime()) / 60000;
    return {
      alive: false,
      serverId,
      failure,
      minutesSinceFailure: Math.round(minutesSinceLastSeen),
      recommendation: getRepairRecommendation(serverId, failure),
    };
  }

  return { alive: true, serverId };
}

// ============================================================
// Repair: attempt to fix known failures
// ============================================================

function getRepairRecommendation(serverId, failure) {
  // Check known server registry
  for (const [name, config] of Object.entries(SERVER_REGISTRY)) {
    if (serverId === name || (config.pattern && config.pattern.test(serverId))) {
      switch (config.repair) {
        case 'restart':
          return {
            strategy: 'restart',
            action: `Server "${name}" dropped. It's a local npx server — restarting may fix it.`,
            canAutoRepair: true,
          };
        case 'reconnect':
          return {
            strategy: 'reconnect',
            action: `Server "${name}" disconnected (${failure.type}). This is a known flaky connection — use ToolSearch to check if tools are available, or proceed without it.`,
            canAutoRepair: false,
            workaround: `Skip ${name} tools and use alternative approaches. The server reconnects on its own when the platform is stable.`,
          };
        case 'wait-and-retry':
          return {
            strategy: 'wait-and-retry',
            action: `Server "${name}" is managed — it should reconnect automatically. Wait and retry.`,
            canAutoRepair: false,
          };
      }
    }
  }

  // Generic repair advice
  if (failure.type === 'CONNECT_TIMEOUT' || failure.type === 'CONNECTION_CLOSED') {
    return {
      strategy: 'reconnect',
      action: `Server "${serverId}" timed out or closed. Use ToolSearch to check if it reconnected.`,
      canAutoRepair: false,
      workaround: 'Proceed with available tools. The server may reconnect on its own.',
    };
  }

  if (failure.type === '404') {
    return {
      strategy: 'skip',
      action: `Server "${serverId}" returned 404 — endpoint may be misconfigured or unavailable.`,
      canAutoRepair: false,
      workaround: 'This server is unavailable for this session. Use alternatives.',
    };
  }

  return {
    strategy: 'manual',
    action: `Server "${serverId}" failed with ${failure.type}. Manual intervention needed.`,
    canAutoRepair: false,
  };
}

function attemptRepair() {
  const state = loadState();
  const results = [];

  for (const [serverId, failure] of Object.entries(state.failures)) {
    const rec = getRepairRecommendation(serverId, failure);

    if (rec.canAutoRepair && failure.repairAttempts < 3) {
      // Only auto-repair local servers, and only 3 times max
      if (rec.strategy === 'restart') {
        const config = SERVER_REGISTRY[serverId];
        if (config && config.type === 'local-npx') {
          try {
            log(`REPAIR: Attempting restart of ${serverId}`);
            // We can't actually restart MCP servers from a hook —
            // but we can flag it for the agent to handle
            failure.repairAttempts++;
            failure.needsRestart = true;
            results.push({
              serverId,
              action: 'flagged-for-restart',
              message: `${serverId} needs restart — run: claude mcp restart ${serverId}`,
            });
          } catch (e) {
            log(`REPAIR FAILED: ${serverId} — ${e.message}`);
          }
        }
      }
    } else {
      results.push({
        serverId,
        action: 'skip',
        reason: rec.canAutoRepair ? 'max attempts reached' : rec.strategy,
        recommendation: rec.action,
        workaround: rec.workaround || null,
      });
    }
  }

  saveState(state);
  return results;
}

// ============================================================
// Status: report current watchdog state
// ============================================================

function getStatus() {
  const state = loadState();
  const failCount = Object.keys(state.failures).length;
  const lines = [];

  if (failCount === 0) {
    lines.push('[MCP Watchdog] All monitored connections healthy');
  } else {
    lines.push(`[MCP Watchdog] ${failCount} connection(s) in failure state:`);
    for (const [id, f] of Object.entries(state.failures)) {
      const age = Math.round((Date.now() - new Date(f.firstSeen).getTime()) / 60000);
      const rec = getRepairRecommendation(id, f);
      lines.push(`  ${id}: ${f.type} (${f.count}x over ${age}min) — ${rec.strategy}`);
      if (rec.workaround) lines.push(`    Workaround: ${rec.workaround}`);
    }
  }

  if (state.connecting && state.connecting.length > 0) {
    lines.push(`  Connecting: ${state.connecting.join(', ')}`);
  }

  return lines.join('\n');
}

// ============================================================
// Main
// ============================================================

const mode = process.argv[2] || 'scan';

switch (mode) {
  case 'scan': {
    // Read from stdin (UserPromptSubmit hook pipes context)
    let input = '';
    try {
      input = fs.readFileSync(0, 'utf8');
    } catch {
      // No stdin — check environment for tool context
      input = process.env.CLAUDE_TOOL_INPUT || '';
    }

    const { foundAny, state } = scanForFailures(input);

    if (foundAny) {
      const failCount = Object.keys(state.failures).length;
      const repairs = attemptRepair();
      const actionable = repairs.filter(r => r.action !== 'skip');

      let output = `[MCP Watchdog] ${failCount} dropped connection(s) detected`;

      // Build repair summary
      for (const r of repairs) {
        if (r.workaround) {
          output += `\n  ${r.serverId}: ${r.workaround}`;
        } else if (r.message) {
          output += `\n  ${r.serverId}: ${r.message}`;
        }
      }

      console.log(output);
    }
    break;
  }

  case 'check': {
    const toolName = process.argv[3] || '';
    const result = checkTool(toolName);
    if (!result.alive) {
      console.log(JSON.stringify({
        blocked: true,
        serverId: result.serverId,
        failureType: result.failure.type,
        minutesSinceFailure: result.minutesSinceFailure,
        recommendation: result.recommendation,
      }));
    }
    break;
  }

  case 'repair': {
    const results = attemptRepair();
    console.log(JSON.stringify(results, null, 2));
    break;
  }

  case 'status': {
    console.log(getStatus());
    break;
  }

  case 'reset': {
    // Clear all failure state — fresh start
    saveState({
      failures: {},
      repairs: {},
      healthy: [],
      sessionStart: new Date().toISOString(),
    });
    log('STATE RESET by user');
    console.log('[MCP Watchdog] State reset');
    break;
  }

  default:
    console.error(`Unknown mode: ${mode}`);
    process.exit(1);
}
