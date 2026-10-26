---
name: "Auto-Deploy Claude Flow"
description: "Automatically initialize and deploy claude-flow v3 into any repository. Runs npx claude-flow@alpha init --force, verifies the output, commits to the active branch, and pushes. Use when onboarding a new repo, bootstrapping a cloud session, or resetting a claude-flow installation."
---

# Auto-Deploy Claude Flow

## What This Skill Does

Performs a fully automatic, zero-prompt deployment of the claude-flow v3 orchestration framework into the current repository. After invocation the repo will have agents, skills, commands, hooks, helpers, MCP config, and the CLAUDE.md swarm guidance file — committed and pushed — with no manual steps.

## When to Use

- First-time setup of a repository for multi-agent swarm orchestration
- Cloud session bootstrap (SessionStart hook or manual trigger)
- Resetting or upgrading an existing claude-flow installation
- Onboarding a new project into the claude-flow ecosystem

## Prerequisites

- Node.js 18+
- Git repository with a remote configured
- A branch to commit to (reads the current branch automatically)

## Quick Start

```bash
# One command — the skill handles everything else
npx claude-flow@alpha init --force
```

## Automatic Deployment Steps

When this skill is invoked, execute every step below **in order** without prompting the user. All independent operations within a step run in parallel.

### Step 1 — Initialize

```bash
npx claude-flow@alpha init --force
```

Expect output confirming directories, files, and integration artifacts created.

### Step 2 — Verify

Run these checks in parallel:

```bash
# Confirm critical files exist
test -f CLAUDE.md && echo "CLAUDE.md OK"
test -f .mcp.json && echo ".mcp.json OK"
test -d .claude/agents && echo "Agents OK"
test -d .claude/skills && echo "Skills OK"
test -d .claude/commands && echo "Commands OK"
test -d .claude/helpers && echo "Helpers OK"
test -f .claude/settings.json && echo "Settings OK"
test -d .claude-flow && echo "Runtime OK"
```

If any check fails, re-run `npx claude-flow@alpha init --force` once and verify again. If still failing, report the missing items to the user and stop.

### Step 3 — Commit

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
git add .claude-flow/ .claude/ .mcp.json CLAUDE.md
git commit -m "Initialize claude-flow v3 with full Claude Code integration

Sets up swarm orchestration framework with agents, skills, commands,
hooks, and runtime configuration for multi-agent coordination."
```

### Step 4 — Push

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
git push -u origin "$BRANCH"
```

If the push fails due to a network error, retry up to 4 times with exponential backoff (2s, 4s, 8s, 16s).

### Step 5 — Report

Print a summary of what was deployed:

| Category | Count | Location |
|----------|-------|----------|
| Agents | .claude/agents/ | Multi-category agent definitions |
| Skills | .claude/skills/ | Reusable skill packages |
| Commands | .claude/commands/ | Slash-command definitions |
| Helpers | .claude/helpers/ | Hook scripts and utilities |
| Runtime | .claude-flow/ | Config, data, logs, sessions |
| MCP | .mcp.json | MCP server configuration |
| Guidance | CLAUDE.md | Swarm behavioral rules |

## Error Handling

| Error | Action |
|-------|--------|
| `npx` not found | Ensure Node.js 18+ is installed |
| Network timeout during init | Retry once after 5s |
| Git push rejected (non-fast-forward) | Pull, rebase, then push |
| Git push network failure | Retry 4x with exponential backoff |
| Missing files after init | Re-run init --force once |

## Post-Deploy Next Steps

After deployment completes, the following commands are available:

```bash
# Start background workers
npx claude-flow@alpha daemon start

# Initialize memory database
npx claude-flow@alpha memory init

# Initialize a swarm
npx claude-flow@alpha swarm init --topology hierarchical --max-agents 8

# Health check
npx claude-flow@alpha doctor --fix
```

## SessionStart Hook Integration

To make this skill run automatically on every new cloud session, add it to `.claude/settings.json` under hooks:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "npx claude-flow@alpha init --force 2>&1 || true"
          }
        ]
      }
    ]
  }
}
```

This ensures every new session starts with claude-flow fully deployed.
