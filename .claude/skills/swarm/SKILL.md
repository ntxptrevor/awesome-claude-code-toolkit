---
name: "Swarm Orchestration"
description: "Multi-agent swarm orchestration: mesh, hierarchical, and adaptive topologies with automatic task distribution, load balancing, fault tolerance, and advanced patterns for research, development, and testing workflows. Use for parallel agent coordination, distributed AI systems, and complex multi-agent pipelines."
---

# Swarm Orchestration

## What This Skill Does

Orchestrates multi-agent swarms using agentic-flow's coordination system. Supports mesh, hierarchical, star, ring, and adaptive topologies with parallel execution, load balancing, fault tolerance, memory coordination, neural pattern learning, and workflow automation.

## Prerequisites

- agentic-flow v1.5.11+, Node.js 18+

## Quick Start

```bash
npx agentic-flow hooks swarm-init --topology mesh --max-agents 5
npx agentic-flow hooks agent-spawn --type coder
npx agentic-flow hooks agent-spawn --type tester
npx agentic-flow hooks agent-spawn --type reviewer
npx agentic-flow hooks task-orchestrate --task "Build REST API with tests" --mode parallel
```

## Topologies

| Topology | Best For | Communication |
|----------|----------|---------------|
| **Mesh** | Research, analysis, brainstorming | Peer-to-peer broadcast |
| **Hierarchical** | Development, structured workflows | Queen-worker delegation |
| **Star** | Testing, validation, QA | Centralized coordination |
| **Ring** | Pipelines, staged processing | Sequential chain |
| **Adaptive** | Mixed workloads | Auto-switches by task complexity |

```typescript
// Mesh
await swarm.init({ topology: 'mesh', agents: ['coder', 'tester', 'reviewer'], communication: 'broadcast' });

// Hierarchical
await swarm.init({ topology: 'hierarchical', queen: 'architect', workers: ['backend-dev', 'frontend-dev'] });

// Adaptive
await swarm.init({ topology: 'adaptive', optimization: 'task-complexity' });
```

## Task Execution Modes

### Parallel

```typescript
const results = await swarm.execute({
  tasks: [
    { agent: 'coder', task: 'Implement API endpoints' },
    { agent: 'frontend', task: 'Build UI components' },
    { agent: 'tester', task: 'Write test suite' }
  ],
  mode: 'parallel', timeout: 300000
});
```

### Pipeline

```typescript
await swarm.pipeline([
  { stage: 'design', agent: 'architect' },
  { stage: 'implement', agent: 'coder', after: 'design' },
  { stage: 'test', agent: 'tester', after: 'implement' },
  { stage: 'review', agent: 'reviewer', after: 'test' }
]);
```

### Auto-Orchestrate

```typescript
await swarm.autoOrchestrate({
  goal: 'Build production-ready API',
  constraints: { maxTime: 3600, maxAgents: 8, quality: 'high' }
});
```

## Swarm Patterns

### Research Swarm (Mesh, 5-6 agents)

```javascript
mcp__claude-flow__swarm_init({ topology: "mesh", maxAgents: 6, strategy: "adaptive" })
// Spawn: 2 researchers, 2 analysts, 1 synthesizer, 1 documenter
// Phase 1: Parallel information gathering
// Phase 2: Pattern recognition + validation
// Phase 3: Knowledge graph construction
// Phase 4: Report generation
```

### Development Swarm (Hierarchical, 6-8 agents)

```javascript
mcp__claude-flow__swarm_init({ topology: "hierarchical", maxAgents: 8, strategy: "balanced" })
// Spawn: 1 architect, 2 devs, 1 db engineer, 1 tester, 1 reviewer, 1 writer, 1 devops
// Phase 1: Architecture design
// Phase 2: Parallel implementation
// Phase 3: Testing + validation
// Phase 4: Review + deployment
```

### Testing Swarm (Star, 5-7 agents)

```javascript
mcp__claude-flow__swarm_init({ topology: "star", maxAgents: 7, strategy: "parallel" })
// Spawn: 1 unit, 1 integration, 1 e2e, 1 perf, 1 security, 1 analyst, 1 documenter
// Parallel test execution → Analysis → Reporting
```

### Analysis Swarm (Mesh, 4-5 agents)

```javascript
mcp__claude-flow__swarm_init({ topology: "mesh", maxAgents: 5, strategy: "adaptive" })
// Spawn: code analyzer, security analyzer, perf analyzer, arch analyzer, reporter
// Parallel analysis → Synthesis → Report
```

## Advanced Features

### Load Balancing & Fault Tolerance

```typescript
await swarm.enableLoadBalancing({ strategy: 'dynamic', metrics: ['cpu', 'memory', 'task-queue'] });
await swarm.setResiliency({ retry: { maxAttempts: 3, backoff: 'exponential' }, fallback: 'reassign-task' });
```

### Memory Coordination

```typescript
await swarm.memory.store('api-schema', { endpoints: [...], models: [...] });
const schema = await swarm.memory.retrieve('api-schema');
```

```javascript
// Namespaced storage with TTL
mcp__claude-flow__memory_usage({
  action: "store", key: "findings-" + Date.now(),
  value: JSON.stringify(data), namespace: "research", ttl: 604800
})

// State snapshots
mcp__claude-flow__state_snapshot({ name: "dev-checkpoint-1" })
mcp__claude-flow__context_restore({ snapshotId: "dev-checkpoint-1" })
```

### Neural Pattern Learning

```javascript
mcp__claude-flow__neural_train({
  pattern_type: "coordination",
  training_data: JSON.stringify(successfulWorkflows), epochs: 50
})
mcp__claude-flow__learning_adapt({
  experience: { workflow: "research-to-report", success: true, duration: 3600, quality: 0.95 }
})
```

### Workflow Automation

```javascript
mcp__claude-flow__workflow_create({
  name: "full-stack-development",
  steps: [
    { phase: "design", agents: ["architect"] },
    { phase: "implement", agents: ["backend-dev", "frontend-dev"], parallel: true },
    { phase: "test", agents: ["tester", "security-tester"], parallel: true },
    { phase: "review", agents: ["reviewer"] },
    { phase: "deploy", agents: ["devops"] }
  ],
  triggers: ["on-commit", "scheduled-daily"]
})
```

### Monitoring

```javascript
mcp__claude-flow__swarm_monitor({ swarmId: "active-swarm", interval: 3000 })
mcp__claude-flow__metrics_collect({ components: ["agents", "tasks", "memory", "performance"] })
mcp__claude-flow__health_check({ components: ["swarm", "agents", "neural", "memory"] })
```

### Performance Optimization

```javascript
mcp__claude-flow__topology_optimize({ swarmId: "current-swarm" })
mcp__claude-flow__load_balance({ swarmId: "dev-swarm", tasks: taskQueue })
mcp__claude-flow__bottleneck_analyze({ component: "application", metrics: ["response-time", "throughput"] })
```

## Best Practices

1. **Topology**: Mesh for research, hierarchical for dev, star for testing, ring for pipelines
2. **Scale**: Start with 2-3 agents, scale up as needed
3. **Memory**: Use namespaces, set TTL, create regular backups
4. **Parallelism**: Identify independent tasks; use sequential for dependencies
5. **Monitoring**: Track health, collect metrics, optimize topology based on performance
6. **Fault tolerance**: Enable auto-recovery, analyze error patterns, create fallback workflows

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Agents not coordinating | Check topology, verify memory access, enable hooks |
| Parallel execution failing | Verify task dependencies, check resource limits |
| Memory persistence issues | Verify namespaces, check TTL, ensure backup config |
| Performance degradation | Optimize topology, reduce agent count, analyze bottlenecks |

## NTXP Interop

This skill participates in the NTXP shared ecosystem. Follow these conventions (see NTXP IPDM skill for full spec):

- **Knowledge Base**: Search `.ntxp/ipdm/project.yaml` and `.ntxp/coda/registry.yaml` before external calls. Save outputs back to `.ntxp/ipdm/project.yaml`.
- **Credentials**: Auth via `ntxp-id` plugin → secrets via `anthropic-skills:ntxp-secrets-vault` → never hardcode.
- **Model Routing**: Read `.ntxp/ipdm/model-council.yaml` for model config. Call `ntxp-model-council` if missing.
- **Skill Bindings**: Check `.ntxp/ipdm/skill-config.yaml` for read/write path declarations.
- **Platform Keys**: Use `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot` — no aliases.
