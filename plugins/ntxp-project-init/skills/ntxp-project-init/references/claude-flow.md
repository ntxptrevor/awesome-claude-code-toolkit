# Claude Flow (RuFlo V3) Reference

Everything from the repo's `CLAUDE.md` that Project Init depends on, reconciled with the NTXP layer.

## Purpose and architecture

Claude Flow is the multi-agent orchestration layer. Claude Code's Task tool does the real work (agents, file ops, code, git). The CLI only coordinates: swarm init, memory, hooks, routing. Never use the CLI as a substitute for Task agents.

| Setting | Value |
|---|---|
| Topology | hierarchical-mesh (use hierarchical for coding swarms) |
| Agents | max 15 configured; keep 6-8 active for tight coordination |
| Strategy | specialized, clear role boundaries |
| Consensus | raft for hive-mind (leader holds authoritative state) |
| Memory | hybrid backend, HNSW enabled, learning bridge and memory graph on |
| Neural | enabled; learning auto-trains on coordination, optimization, prediction |
| Domain model | DDD with bounded contexts, event sourcing for state changes |
| Code rules | files under 500 lines, typed interfaces on public APIs, TDD London School for new code, validate input at system boundaries |

## File organization

Source in `/src`, tests `/tests`, docs `/docs`, config `/config`, scripts `/scripts`, examples `/examples`. Never save working files to the repo root.

## Optimization plan: 3-tier routing (ADR-026)

| Tier | Handler | Latency | Cost | Use |
|---|---|---|---|---|
| 1 | Agent Booster (WASM) | <1ms | $0 | Simple transforms, skip the LLM |
| 2 | Haiku | ~500ms | ~$0.0002 | Low complexity (<30%) |
| 3 | Sonnet/Opus | 2-5s | $0.003-0.015 | Reasoning, architecture, security (>30%) |

Check for `[AGENT_BOOSTER_AVAILABLE]` or `[TASK_MODEL_RECOMMENDATION]` before spawning agents; use Edit directly when the booster is available. NTXP Highway uses the same tiers for skill routing, so the two plans are one: Highway picks the skill, the tier picks the model.

## Swarm execution rules

- Initialize with `npx @claude-flow/cli@3.75.3 swarm init --topology hierarchical --max-agents 8 --strategy specialized`
- Spawn all agents in one message with `run_in_background: true`, then stop. Do not poll status.
- Review all returned results before proceeding.
- Run checkpoints through `post-task` hooks; share one memory namespace across agents.

## CLI commands

| Command | Purpose |
|---|---|
| `init` | Project initialization |
| `agent` | Agent lifecycle (spawn, list) |
| `swarm` | Swarm coordination |
| `memory` | AgentDB memory with HNSW search |
| `task` | Task creation and lifecycle |
| `session` | Session state |
| `hooks` | Self-learning hooks and 12 workers |
| `hive-mind` | Fault-tolerant consensus |
| `doctor --fix` | Health check and repair |

Memory: `memory store --key K --value V --namespace N`, `memory search --query Q`, `memory list --namespace N`, `memory retrieve --key K`.

## Agents (core set)

core: coder, reviewer, tester, planner, researcher. Specialized: security-architect, security-auditor, memory-specialist, performance-engineer. Coordination: hierarchical-, mesh-, adaptive-coordinator. GitHub: pr-manager, code-review-swarm, issue-tracker, release-manager. SPARC: sparc-coord, sparc-coder, specification, pseudocode, architecture.

## Hooks installed by init

PreToolUse (Bash guard, edit tracking), PostToolUse, UserPromptSubmit (routing), SessionStart (restore, memory import), SessionEnd, Stop, PreCompact, SubagentStart/Stop, Notification. Hook contract reminders: command input arrives on stdin as JSON (`tool_input.command`, `tool_input.file_path`); a blocking guard must exit 2; hook `timeout` is in seconds.

## Security rules

Never hardcode keys or commit `.env`. Validate input at boundaries. Sanitize file paths. Run the security scan after security-related changes. Pin the CLI (`@claude-flow/cli@3.75.3`, set in `.mcp.json`); never `@latest`. Keep `npx` allow rules narrow.

## Reconciliation with NTXP

| Claude Flow piece | NTXP counterpart | Rule |
|---|---|---|
| `.claude-flow/` runtime state | `.ntxp/` project data | Runtime stays git-ignored; `.ntxp/` project data is committed |
| Hybrid memory / HNSW | IPDM + Coda (project knowledge base) | Project facts live in `.ntxp/`; learned patterns live in Claude Flow memory |
| 3-tier routing | Highway routing + Model Council | Highway picks skill, Council picks model |
| Swarm of Task agents | NTXP skills | Agents invoke skills; skills never spawn swarms on their own |
| Watchdog / `doctor` | `mcp-watchdog.cjs`, ntxp-autonomous-repair | Watchdog detects, repair skill acts |
