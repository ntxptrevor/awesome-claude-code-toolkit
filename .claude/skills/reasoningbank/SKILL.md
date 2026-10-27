---
name: "ReasoningBank"
description: "Adaptive learning with ReasoningBank: trajectory tracking, verdict judgment, memory distillation, pattern recognition, and AgentDB-powered vector search for experience replay. Use for self-learning agents, decision optimization, meta-cognitive systems, and experience-driven improvement."
---

# ReasoningBank

## What This Skill Does

ReasoningBank enables agents to learn from experience using AgentDB's high-performance vector backend (150x-12,500x faster). Covers trajectory tracking, verdict judgment, memory distillation, pattern recognition, strategy optimization, and meta-cognitive learning.

**Performance**: 150x faster pattern retrieval, 500x faster batch ops, <1ms memory access.

## Prerequisites

- Node.js 18+, AgentDB v1.0.7+ (via agentic-flow), agentic-flow v1.5.11+

## Quick Start

### CLI Setup

```bash
npx agentdb@latest init ./.agentdb/reasoningbank.db --dimension 1536
npx agentdb@latest mcp
claude mcp add agentdb npx agentdb@latest mcp
```

### API Setup

```typescript
import { createAgentDBAdapter, computeEmbedding } from 'agentic-flow/reasoningbank';

const rb = await createAgentDBAdapter({
  dbPath: '.agentdb/reasoningbank.db',
  enableLearning: true,
  enableReasoning: true,
  cacheSize: 1000,
});
```

## Core Concepts

### 1. Trajectory Tracking

Record agent execution paths and outcomes:

```typescript
const trajectory = {
  task: 'optimize-api-endpoint',
  steps: [
    { action: 'analyze-bottleneck', result: 'found N+1 query' },
    { action: 'add-eager-loading', result: 'reduced queries' },
    { action: 'add-caching', result: 'improved latency' }
  ],
  outcome: 'success',
  metrics: { latency_before: 2500, latency_after: 150 }
};

const embedding = await computeEmbedding(JSON.stringify(trajectory));
await rb.insertPattern({
  id: '', type: 'trajectory', domain: 'api-optimization',
  pattern_data: JSON.stringify({ embedding, pattern: trajectory }),
  confidence: 0.9, usage_count: 1, success_count: 1,
  created_at: Date.now(), last_used: Date.now(),
});
```

### 2. Verdict Judgment

Judge whether a trajectory was successful by comparing against past patterns:

```typescript
const similar = await rb.retrieveWithReasoning(queryEmbedding, {
  domain: 'api-optimization', k: 10,
});
const verdict = similar.memories.filter(m =>
  m.pattern.outcome === 'success' && m.similarity > 0.8
).length > 5 ? 'likely_success' : 'needs_review';
```

### 3. Memory Distillation

Consolidate similar experiences into high-level patterns:

```typescript
const experiences = await rb.retrieveWithReasoning(embedding, {
  domain: 'api-optimization', k: 100, optimizeMemory: true,
});
const distilled = {
  domain: 'api-optimization',
  pattern: 'For N+1 queries: add eager loading, then cache',
  success_rate: 0.92, sample_size: experiences.memories.length,
};
```

### 4. Pattern Recognition & Strategy Optimization

```typescript
// Learn patterns
await rb.learnPattern({
  pattern: 'api_errors_increase_after_deploy',
  triggers: ['deployment', 'traffic_spike'],
  actions: ['rollback', 'scale_up'],
  confidence: 0.85
});

// Compare strategies
const comparison = await rb.compareStrategies('bug_fixing', [
  'tdd_approach', 'debug_first', 'reproduce_then_fix'
]);

// Get best strategy for context
const strategy = await rb.recommendStrategy('code_review', {
  language: 'typescript', complexity: 'high'
});
```

### 5. Meta-Learning & Transfer

```typescript
// Learn about learning
await rb.metaLearn({
  observation: 'parallel_execution_faster_for_independent_tasks',
  confidence: 0.95,
  applicability: { task_types: ['batch_processing'], conditions: ['tasks_independent'] }
});

// Transfer knowledge across domains
await rb.transferKnowledge({
  from: 'code_review_javascript', to: 'code_review_typescript', similarity: 0.8
});
```

## Reasoning Modules

AgentDB provides 4 reasoning modules activated via `retrieveWithReasoning`:

| Module | Flag | Purpose |
|--------|------|---------|
| PatternMatcher | `useMMR: true` | Diverse, relevant memory retrieval |
| ContextSynthesizer | `synthesizeContext: true` | Coherent narrative from multiple memories |
| MemoryOptimizer | `optimizeMemory: true` | Consolidate similar patterns, prune low-quality |
| ExperienceCurator | `minConfidence: 0.8` | Filter by quality and relevance |

```typescript
const result = await rb.retrieveWithReasoning(queryEmbedding, {
  domain: 'code-optimization',
  k: 10, useMMR: true, synthesizeContext: true,
});
```

## Adaptive Agents

```typescript
class AdaptiveAgent {
  async execute(task: Task) {
    const strategy = await rb.recommendStrategy(task.type, task.context);
    const result = await this.executeWithStrategy(task, strategy);
    await rb.recordExperience({
      task: task.type, approach: strategy.name,
      outcome: result, context: task.context
    });
    return result;
  }
}
```

## Hierarchical Memory

```typescript
// Low-level: specific fix
await rb.insertPattern({ type: 'concrete', domain: 'debugging/null-pointer', ... });
// Mid-level: pattern across cases
await rb.insertPattern({ type: 'pattern', domain: 'debugging', ... });
// High-level: general principle
await rb.insertPattern({ type: 'principle', domain: 'software-engineering', ... });
```

## Legacy API Compatibility

100% backward compatible with legacy ReasoningBank:

```typescript
import { retrieveMemories, judgeTrajectory, distillMemories } from 'agentic-flow/reasoningbank';
const memories = await retrieveMemories(query, { domain: 'code-generation', agent: 'coder' });
const verdict = await judgeTrajectory(trajectory, query);
const newMemories = await distillMemories(trajectory, verdict, query, { domain: 'code-generation' });
```

## CLI Operations

```bash
npx agentdb@latest export ./.agentdb/reasoningbank.db ./backup.json
npx agentdb@latest import ./experiences.json
npx agentdb@latest stats ./.agentdb/reasoningbank.db
npx agentdb@latest migrate --source .swarm/memory.db --target .agentdb/reasoningbank.db
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Migration fails | Check source DB exists; run with `DEBUG=agentdb:*` |
| Low confidence scores | Enable `synthesizeContext: true` and `useMMR: true` |
| Memory growing too large | Enable `optimizeMemory: true` or call `rb.optimize()` |
| Poor recommendations | Need 100+ experiences per task type |
| Slow pattern matching | Enable vector indexing in AgentDB |

## NTXP Interop

This skill participates in the NTXP shared ecosystem. Follow these conventions (see NTXP IPDM skill for full spec):

- **Knowledge Base**: Search `.ntxp/ipdm/project.yaml` and `.ntxp/coda/registry.yaml` before external calls. Save outputs back to `.ntxp/ipdm/project.yaml`.
- **Credentials**: Auth via `ntxp-id` plugin → secrets via `anthropic-skills:ntxp-secrets-vault` → never hardcode.
- **Model Routing**: Read `.ntxp/ipdm/model-council.yaml` for model config. Call `ntxp-model-council` if missing.
- **Skill Bindings**: Check `.ntxp/ipdm/skill-config.yaml` for read/write path declarations.
- **Platform Keys**: Use `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot` — no aliases.
