---
name: "V3 Operations"
description: "Claude-flow v3 operations: CLI modernization with hooks, unified AgentDB memory (150x-12,500x search improvement), performance benchmarking (2.49x-7.47x speedup), and 15-agent hierarchical swarm coordination. Use for v3 CLI features, memory unification, performance targets, and swarm orchestration."
---

# V3 Operations

Consolidated from: v3-cli-modernization, v3-memory-unification, v3-performance-optimization, v3-swarm-coordination.

## CLI Modernization

### Target Architecture

```
Current:  index.ts (108KB monolith), basic command parsing
Target:   Modular commands (<500 lines each), smart prompts, <200ms response
```

### Key Components

- **ModularCommandRegistry**: Hash index + alias + fuzzy match, per-command middleware
- **InteractivePromptService**: select, multiSelect, input, confirm, progressTask (inquirer-based, dynamic import for tree-shaking)
- **CLIHooksManager**: Deep lifecycle hooks — `command_start`, `command_end`, `command_error`, `agent_spawn`, `task_complete`
- **WorkflowOrchestrator**: Multi-step workflows with dependency DAG, conditions, retry policies, intent-to-workflow generation
- **IntelligentCompletion**: Learning-based suggestions + context-aware (git repo, package.json detection)
- **CommandPerformanceMonitor**: Per-command P95 latency, memory delta, success rate, regression alerts

### Learning Integration

Hooks integrate with SONA/AgentDB for continuous improvement:

```
command_start → trajectoryStart + recordExperience
command_end   → trajectoryEnd + submitFeedback (reward = success + speed + complexity)
command_error → trajectoryEnd(negative) + learn from failure
reward > 0.8  → storePattern for future suggestion
```

## Memory Unification (ADR-006, ADR-009)

### 7 Legacy Systems → AgentDB

```
MemoryManager, DistributedMemorySystem, SwarmMemory,
AdvancedMemoryManager, SQLiteBackend, MarkdownBackend, HybridBackend
                    ↓
            AgentDB with HNSW
  • 150x-12,500x faster search
  • Unified query interface
  • Cross-agent memory sharing
  • SONA learning integration
```

### Core Implementation

```typescript
class UnifiedMemoryService implements IMemoryBackend {
  async store(entry) { await agentdb.store(entry); await indexer.index(entry); }
  async query(query) {
    if (query.semantic) return indexer.search(query); // HNSW path
    return agentdb.query(query);                      // Structured path
  }
}

class HNSWIndexer {
  // dimensions: 1536, efConstruction: 200, M: 16
  async search(query) {
    const embedding = await embedContent(query.content);
    return index.search(embedding, query.limit || 10);
  }
}
```

### Migration

1. **Foundation**: AgentDB adapter with HNSW config
2. **Data Migration**: SQLite rows → AgentDB (with embeddings); Markdown files → AgentDB (with metadata)
3. **SONA Integration**: Learning patterns stored as semantic-searchable memory entries

## Performance Optimization

### Target Matrix

| Metric | Current | Target | Method |
|--------|---------|--------|--------|
| Flash Attention | Standard attention | 2.49x-7.47x speedup | agentic-flow@alpha |
| Search | O(n) linear | 150x-12,500x | HNSW indexing |
| Memory | Full dataset in heap | 50-75% reduction | Pooling + compression |
| Startup | ~1.8s | <500ms | Connection pool + pre-built index |
| SONA Adaptation | N/A | <0.05ms | Real-time RL mode |
| 15-Agent Coordination | Sequential | >85% utilization | Hierarchical mesh |

### Benchmark Suite

```bash
npm run benchmark:v3                  # Full suite
npm run benchmark:flash-attention     # Attention speedup
npm run benchmark:agentdb-search      # HNSW search speed
npm run benchmark:memory-optimization # Heap reduction
npm run monitor:performance           # Continuous dashboard
```

### Regression Detection

5% threshold — any metric that drops below baseline triggers alert with severity classification and fix recommendations.

## 15-Agent Swarm Coordination

### Hierarchical Mesh Topology

```
                    Queen Coordinator (#1)
                         │
        ┌────────────────┼────────────────┐
   SECURITY (#2-4)    CORE (#5-9)    INTEGRATION (#10-12)
        └────────────────┼────────────────┘
                         │
        ┌────────────────┼────────────────┐
   QUALITY (#13)    PERFORMANCE (#14)  DEPLOYMENT (#15)
```

### 14-Week Phased Execution

| Phase | Weeks | Agents | Focus |
|-------|-------|--------|-------|
| Foundation | 1-2 | #1-6 | Security CVE fixes + DDD architecture |
| Core Systems | 3-6 | #1, #5-9, #13 | AgentDB, swarm unification, MCP, TDD |
| Integration | 7-10 | #1, #10-14 | agentic-flow integration, CLI, SONA, benchmarks |
| Release | 11-14 | All 15 | Final optimization, CI/CD, v3.0.0 release |

### Coordination Patterns

- **Dependency DAG**: Security (#2) has no deps → Core (#5) depends on security → Integration (#10) depends on core
- **QUIC Communication Bus**: Broadcast to security/core/integration domains with priority routing
- **Load Balancing**: Monitor agent workloads, redistribute when capacity threshold exceeded
- **GitHub Integration**: Milestone tracking, epic issues per domain, hourly progress updates

### Agent Roster

| Domain | Agents | Roles |
|--------|--------|-------|
| Orchestration | #1 | Queen Coordinator — issues, deps, timeline |
| Security | #2-4 | Architect, Implementer, Tester |
| Core | #5-9 | Architect, Implementer, Memory, Swarm, MCP |
| Integration | #10-12 | agentic-flow Architect, CLI/Hooks Dev, Neural/Learning |
| Cross-cutting | #13-15 | TDD Engineer, Performance Engineer, Release Engineer |

## Success Metrics

- CLI: <200ms response, <10KB per command module, >90% completion accuracy
- Memory: All 7 systems migrated, 150x-12,500x search validated, 50-75% heap reduction
- Performance: Flash Attention 2.49x-7.47x, SONA <0.05ms, startup <500ms
- Swarm: >85% agent utilization, zero deadlocks, <100ms inter-agent messaging, 14-week delivery

## NTXP Interop

This skill participates in the NTXP shared ecosystem. Follow these conventions (see NTXP IPDM skill for full spec):

- **Knowledge Base**: Search `.ntxp/ipdm/project.yaml` and `.ntxp/coda/registry.yaml` before external calls. Save outputs back to `.ntxp/ipdm/project.yaml`.
- **Credentials**: Auth via `ntxp-id` plugin → secrets via `anthropic-skills:ntxp-secrets-vault` → never hardcode.
- **Model Routing**: Read `.ntxp/ipdm/model-council.yaml` for model config. Call `ntxp-model-council` if missing.
- **Skill Bindings**: Check `.ntxp/ipdm/skill-config.yaml` for read/write path declarations.
- **Platform Keys**: Use `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot` — no aliases.
