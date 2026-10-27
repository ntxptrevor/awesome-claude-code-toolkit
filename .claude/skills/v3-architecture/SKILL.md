---
name: "V3 Architecture"
description: "Claude-flow v3 architecture: DDD bounded contexts, clean architecture patterns, deep agentic-flow integration (ADR-001), MCP optimization, and security overhaul (CVE remediation). Use for v3 system design, module structure, integration patterns, and security hardening."
---

# V3 Architecture

Consolidated from: v3-ddd-architecture, v3-core-implementation, v3-integration-deep, v3-mcp-optimization, v3-security-overhaul.

## DDD Bounded Contexts

### Target Architecture

```
src/core/
├── kernel/                     # Microkernel pattern
│   ├── claude-flow-kernel.ts
│   ├── domain-registry.ts
│   └── plugin-loader.ts
├── domains/                    # Bounded contexts
│   ├── task-management/        # Entities, VOs, services, repos, events
│   ├── session-management/
│   ├── health-monitoring/
│   ├── lifecycle-management/
│   └── event-coordination/
├── shared/                     # Shared kernel
│   ├── domain/                 # Entity, ValueObject, AggregateRoot, DomainEvent
│   ├── infrastructure/         # EventBus, DI container, Logger
│   └── types/
└── application/                # Use cases, commands, queries, handlers
```

### Clean Architecture Layers

```
┌─────────────────────────────────────────┐
│              Presentation               │  CLI, API, UI
├─────────────────────────────────────────┤
│              Application                │  Use Cases, Commands
├─────────────────────────────────────────┤
│               Domain                    │  Entities, Services, Events
├─────────────────────────────────────────┤
│            Infrastructure               │  DB, MCP, External APIs
└─────────────────────────────────────────┘
Dependency direction: Outside → Inside. Domain has NO external deps.
```

### Core Patterns

- **Microkernel**: `ClaudeFlowKernel` loads domain modules and plugins dynamically
- **Domain Events**: Cross-domain communication via `DomainEventBus` (TaskAssigned, TaskCompleted, etc.)
- **Plugin Architecture**: Core domains + optional plugins (swarm-coordination, learning-integration)
- **DI Container**: Inversify-based, with repository and service injection
- **God Object Elimination**: orchestrator.ts (1,440 lines) → 5 focused domains (<300 lines each)

### Key Base Classes

```typescript
abstract class Entity<T> { _id, _domainEvents, equals(), addDomainEvent(), getUncommittedEvents() }
abstract class ValueObject<T> { props (frozen), equals(), value }
abstract class AggregateRoot<T> extends Entity<T> { _version, applyEvent() }
```

## Deep agentic-flow Integration (ADR-001)

### Code Deduplication

```
claude-flow           agentic-flow
SwarmCoordinator  →   Swarm System       80% overlap (eliminate)
AgentManager      →   Agent Lifecycle    70% overlap (eliminate)
TaskScheduler     →   Task Execution     60% overlap (eliminate)
SessionManager    →   Session Mgmt       50% overlap (eliminate)

TARGET: <5,000 lines orchestration (vs 15,000+)
```

### Integration Points

- **SONA Learning**: 5 modes (real-time ~0.05ms, balanced, research, edge, batch)
- **Flash Attention**: 2.49x-7.47x speedup, 50-75% memory reduction
- **AgentDB Coordination**: HNSW indexing, 150x-12,500x search speedup
- **MCP Tools**: 213 pre-built tools + 19 hook types
- **RL Algorithms**: PPO, DQN, A2C, MCTS, Q-Learning, SARSA, Actor-Critic, Decision-Transformer

### Migration Strategy

1. **Adapter Layer** — `ClaudeFlowAgent extends AgenticFlowAgent` with backward compat
2. **System Migration** — Replace SwarmCoordinator (800+ lines), AgentManager (1,736+ lines), TaskScheduler (500+ lines)
3. **Cleanup** — Remove deprecated code, validate 100% feature parity

## MCP Server Optimization

### Performance Targets

| Metric | Current | Target |
|--------|---------|--------|
| Startup | ~1.8s | <400ms (4.5x improvement) |
| Tool Lookup | O(n) linear | <5ms O(1) hash table |
| Connection Reuse | 0% | >90% pool hits |
| Response Time | Variable | <100ms p95 |
| Memory | High idle usage | 50% reduction |

### Key Components

- **ConnectionPool**: Min 5, max 50 connections; idle timeout; health checks; LRU eviction
- **FastToolRegistry**: O(1) hash lookup + fuzzy matching + LRU cache (1000 entries) + category index
- **MCPLoadBalancer**: Round-robin, least-connections, response-time, weighted strategies
- **OptimizedTransport**: Message batching + gzip compression + urgent bypass
- **MultiLevelCache**: L1 (in-memory) → L2 (LRU 10k) → L3 (disk) with auto-promotion

## Security Overhaul

### Critical CVE Fixes

| CVE | Issue | Fix |
|-----|-------|-----|
| CVE-1 | Vulnerable deps | `npm update @anthropic-ai/claude-code@^2.0.31` |
| CVE-2 | SHA-256 + hardcoded salt | bcrypt with 12 rounds |
| CVE-3 | Hardcoded credentials | `crypto.randomBytes(32)` |

### Security Patterns

- **Input Validation**: Zod schemas at all boundaries
- **Path Sanitization**: Resolve + prefix check against directory traversal
- **Safe Execution**: `execFile` with `shell: false` (no shell interpretation)
- **Target Score**: 90/100 (npm audit + custom scans), >95% security-critical test coverage

## TypeScript Configuration

```json
{
  "compilerOptions": {
    "target": "ES2022", "module": "NodeNext", "strict": true,
    "exactOptionalPropertyTypes": true, "noUncheckedIndexedAccess": true,
    "experimentalDecorators": true, "emitDecoratorMetadata": true,
    "paths": { "@core/*": ["src/core/*"], "@domains/*": ["src/core/domains/*"] }
  }
}
```

## Success Metrics

- God Object Elimination: orchestrator.ts → 5 focused domains (<300 lines each)
- Code Reduction: <5,000 lines (vs 15,000+)
- MCP Startup: <400ms, Tool Lookup: <5ms, Pool Hits: >90%, Response: <100ms p95
- Security Score: 90/100, all CVEs fixed, >95% security test coverage
- Type Safety: Strict TypeScript, zero `any` types
- Test Coverage: >90% domain logic (London School TDD)

## NTXP Interop

This skill participates in the NTXP shared ecosystem. Follow these conventions (see NTXP IPDM skill for full spec):

- **Knowledge Base**: Search `.ntxp/ipdm/project.yaml` and `.ntxp/coda/registry.yaml` before external calls. Save outputs back to `.ntxp/ipdm/project.yaml`.
- **Credentials**: Auth via `ntxp-id` plugin → secrets via `anthropic-skills:ntxp-secrets-vault` → never hardcode.
- **Model Routing**: Read `.ntxp/ipdm/model-council.yaml` for model config. Call `ntxp-model-council` if missing.
- **Skill Bindings**: Check `.ntxp/ipdm/skill-config.yaml` for read/write path declarations.
- **Platform Keys**: Use `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot` — no aliases.
