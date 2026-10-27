---
name: "AgentDB"
description: "Unified AgentDB skill covering vector search, memory patterns, learning plugins, performance optimization, and advanced distributed features. Use for semantic search, persistent agent memory, reinforcement learning, HNSW indexing, quantization, and multi-database coordination."
---

# AgentDB

## What This Skill Does

AgentDB is a high-performance vector database for AI agents providing **150x-12,500x faster** operations than traditional solutions. It covers five domains in one skill: semantic vector search with HNSW indexing, persistent memory patterns for stateful agents, 9 reinforcement learning algorithms via plugins, performance optimization through quantization and caching, and advanced distributed features including QUIC synchronization and multi-database sharding.

## Quick Start

```bash
# Initialize database
npx agentdb@latest init ./vectors.db --preset medium

# Store and query vectors
npx agentdb@latest query ./vectors.db "[0.1,0.2,0.3,...]" -k 10 -m cosine

# Run benchmarks
npx agentdb@latest benchmark

# Start MCP server for Claude Code
npx agentdb@latest mcp
claude mcp add agentdb npx agentdb@latest mcp

# Create learning plugin
npx agentdb@latest create-plugin -t decision-transformer -n my-agent
```

```typescript
import { createAgentDBAdapter, computeEmbedding } from 'agentic-flow/reasoningbank';

const adapter = await createAgentDBAdapter({
  dbPath: '.agentdb/vectors.db',
  enableLearning: true,
  enableReasoning: true,
  quantizationType: 'scalar',
  cacheSize: 1000,
});
```

---

## Vector Search

Sub-millisecond semantic search with HNSW indexing, multiple distance metrics, and hybrid filtering.

### Store and Search

```typescript
// Store document with embedding
const embedding = await computeEmbedding("quantum computing advances");
await adapter.insertPattern({
  id: '', type: 'document', domain: 'technology',
  pattern_data: JSON.stringify({ embedding, text: "...", metadata: { category: "quantum" } }),
  confidence: 1.0, usage_count: 0, success_count: 0,
  created_at: Date.now(), last_used: Date.now(),
});

// Semantic search with MMR for diverse results
const results = await adapter.retrieveWithReasoning(queryEmbedding, {
  domain: 'technology', k: 10, useMMR: true, synthesizeContext: true,
});
```

### Hybrid Search (Vector + Metadata)

```typescript
const results = await adapter.retrieveWithReasoning(queryEmbedding, {
  domain: 'research-papers', k: 20,
  filters: { year: { $gte: 2023 }, category: 'machine-learning', citations: { $gte: 50 } },
});
```

### Distance Metrics

| Metric | Best For | CLI Flag |
|--------|----------|----------|
| Cosine (default) | Text embeddings, semantic similarity | `-m cosine` |
| Euclidean (L2) | Spatial data, image embeddings | `-m euclidean` |
| Dot Product | Pre-normalized vectors, fast compute | `-m dot` |

### RAG Pipeline

```typescript
async function ragQuery(question: string) {
  const context = await db.searchSimilar(await embed(question), { limit: 5, threshold: 0.7 });
  return await llm.generate(`Context: ${context.map(c => c.text).join('\n')}\nQuestion: ${question}`);
}
```

---

## Memory Patterns

Persistent memory for stateful agents — session memory, long-term facts, pattern learning, and hierarchical organization.

### Session Memory

```typescript
class SessionMemory {
  async storeMessage(role: string, content: string) {
    return await db.storeMemory({ sessionId: this.sessionId, role, content, timestamp: Date.now() });
  }
  async getSessionHistory(limit = 20) {
    return await db.query({ filters: { sessionId: this.sessionId }, orderBy: 'timestamp', limit });
  }
}
```

### Long-Term Memory

```typescript
await db.storeFact({ category: 'user_preference', key: 'language', value: 'English', confidence: 1.0 });
const prefs = await db.getFacts({ category: 'user_preference' });
```

### Hierarchical Memory

```typescript
await memory.organize({
  immediate: recentMessages,   // Last 10 messages
  shortTerm: sessionContext,   // Current session
  longTerm: importantFacts,    // Persistent facts
  semantic: embeddedKnowledge  // Vector search
});
```

### Memory Consolidation

```typescript
await memory.consolidate({ strategy: 'importance', maxSize: 10000, minScore: 0.5 });
```

---

## Learning Plugins

9 reinforcement learning algorithms via AgentDB's plugin system. Train models 10-100x faster with WASM-accelerated inference.

### Available Algorithms

| # | Algorithm | Type | Best For |
|---|-----------|------|----------|
| 1 | **Decision Transformer** | Offline RL | Historical data, imitation learning (recommended) |
| 2 | **Q-Learning** | Value-Based (Off-Policy) | Discrete actions, sample efficiency |
| 3 | **SARSA** | Value-Based (On-Policy) | Safe exploration, risk-sensitive |
| 4 | **Actor-Critic** | Policy Gradient | Continuous actions, multi-agent |
| 5 | **Active Learning** | Query-Based | Human-in-the-loop, label-efficient |
| 6 | **Adversarial Training** | Robustness | Security, adversarial defense |
| 7 | **Curriculum Learning** | Progressive Difficulty | Complex multi-stage tasks |
| 8 | **Federated Learning** | Distributed | Privacy-preserving, multi-agent |
| 9 | **Multi-Task Learning** | Transfer | Related tasks, domain adaptation |

### Create and Train

```bash
npx agentdb@latest create-plugin -t decision-transformer -n my-agent
npx agentdb@latest list-plugins
npx agentdb@latest plugin-info my-agent
```

```typescript
// Store experience → Train → Infer
await adapter.insertPattern({
  id: '', type: 'experience', domain: 'game-playing',
  pattern_data: JSON.stringify({
    embedding: await computeEmbedding('state-action-reward'),
    pattern: { state: [0.1, 0.2], action: 2, reward: 1.0, next_state: [0.15, 0.25], done: false }
  }),
  confidence: 0.9, usage_count: 1, success_count: 1,
  created_at: Date.now(), last_used: Date.now(),
});

const metrics = await adapter.train({ epochs: 50, batchSize: 32 });
```

### Reasoning Agents (4 Modules)

1. **PatternMatcher** — HNSW-indexed similar pattern search
2. **ContextSynthesizer** — Rich context from multiple sources
3. **MemoryOptimizer** — Consolidate similar patterns, prune low-quality
4. **ExperienceCurator** — Quality-based experience filtering

---

## Performance Optimization

### Quantization Strategies

| Type | Memory Reduction | Speed Gain | Accuracy | Best For |
|------|-----------------|------------|----------|----------|
| Binary | 32x | 10x | 95-98% | Large-scale (1M+), mobile/edge |
| Scalar | 4x | 3x | 98-99% | Production, balanced |
| Product | 8-16x | 5x | 93-97% | High-dimensional embeddings |
| None | 1x | 1x | 100% | Maximum accuracy, small datasets |

```typescript
const adapter = await createAgentDBAdapter({ quantizationType: 'binary' }); // 32x reduction
```

### HNSW Indexing

O(log n) search — automatic with AgentDB:

```typescript
const adapter = await createAgentDBAdapter({
  hnswM: 16,               // Connections per layer (8 small, 16 medium, 32 large)
  hnswEfConstruction: 200,  // Build quality
  hnswEfSearch: 100,        // Search quality (50 fast, 100 balanced, 200 high-recall)
});
```

### Optimization Recipes

| Recipe | Quantization | Cache | HNSW M | Result |
|--------|-------------|-------|--------|--------|
| Max Speed | binary | 5000 | 8 | <50us, 90-95% accuracy |
| Balanced | scalar | 1000 | 16 | <100us, 98-99% accuracy |
| Max Accuracy | none | 2000 | 32 | <200us, 100% accuracy |
| Mobile/Edge | binary | 100 | 8 | <100us, ~10MB/100K vectors |

### Benchmarks

| Operation | 10K Vectors | 100K Vectors | 1M Vectors |
|-----------|-------------|-------------|------------|
| Search (optimized) | 100us | 120us | 8ms |
| Search (unoptimized) | 15ms | 150ms | 100s |
| Improvement | 150x | 1,250x | 12,500x |

---

## Advanced Features

### QUIC Synchronization

Sub-millisecond cross-node sync with TLS 1.3, multiplexed streams, and automatic retry:

```typescript
const adapter = await createAgentDBAdapter({
  enableQUICSync: true,
  syncPort: 4433,
  syncPeers: ['192.168.1.10:4433', '192.168.1.11:4433'],
  syncInterval: 1000, syncBatchSize: 100, compression: true,
});
// Patterns auto-sync across all peers within ~1ms
```

### Multi-Database Sharding

```typescript
const shards = {
  knowledge: await createAgentDBAdapter({ dbPath: '.agentdb/knowledge.db' }),
  conversations: await createAgentDBAdapter({ dbPath: '.agentdb/conversations.db' }),
  code: await createAgentDBAdapter({ dbPath: '.agentdb/code.db' }),
};
```

### ReasoningBank Migration

```bash
npx agentdb@latest migrate --source .swarm/memory.db
```

### CLI Reference

```bash
npx agentdb@latest init ./db --preset medium     # Initialize
npx agentdb@latest query ./db "[...]" -k 10      # Search
npx agentdb@latest stats ./db                     # Statistics
npx agentdb@latest export ./db ./backup.json      # Export
npx agentdb@latest import ./backup.json           # Import
npx agentdb@latest benchmark                      # Benchmark
npx agentdb@latest create-plugin -t q-learning    # Create plugin
npx agentdb@latest list-plugins                   # List plugins
npx agentdb@latest mcp                            # MCP server
```

### Environment Variables

```bash
AGENTDB_PATH=.agentdb/reasoningbank.db
AGENTDB_QUANTIZATION=scalar    # binary|scalar|product|none
AGENTDB_CACHE_SIZE=2000
AGENTDB_HNSW_M=16
AGENTDB_LEARNING=true
AGENTDB_REASONING=true
AGENTDB_QUIC_SYNC=true
AGENTDB_QUIC_PORT=4433
AGENTDB_QUIC_PEERS=host1:4433,host2:4433
```

## Learn More

- GitHub: https://github.com/ruvnet/agentic-flow/tree/main/packages/agentdb
- Website: https://agentdb.ruv.io
- MCP: `npx agentdb@latest mcp`
- CLI Help: `npx agentdb@latest --help`

## NTXP Interop

This skill participates in the NTXP shared ecosystem. Follow these conventions (see NTXP IPDM skill for full spec):

- **Knowledge Base**: Search `.ntxp/ipdm/project.yaml` and `.ntxp/coda/registry.yaml` before external calls. Save outputs back to `.ntxp/ipdm/project.yaml`.
- **Credentials**: Auth via `ntxp-id` plugin → secrets via `anthropic-skills:ntxp-secrets-vault` → never hardcode.
- **Model Routing**: Read `.ntxp/ipdm/model-council.yaml` for model config. Call `ntxp-model-council` if missing.
- **Skill Bindings**: Check `.ntxp/ipdm/skill-config.yaml` for read/write path declarations.
- **Platform Keys**: Use `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot` — no aliases.
