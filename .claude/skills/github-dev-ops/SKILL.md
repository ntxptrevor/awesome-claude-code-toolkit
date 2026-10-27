---
name: "GitHub Dev Ops"
description: "Unified GitHub development operations: AI-powered code review with swarm coordination, CI/CD workflow automation, and multi-repo synchronization. Use for PR reviews, GitHub Actions pipelines, cross-repo coordination, and automated quality gates."
---

# GitHub Dev Ops

Unified skill combining code review, workflow automation, and multi-repo coordination. Replaces the standalone `github-code-review`, `github-workflow-automation`, and `github-multi-repo` skills.

## Quick Start

```bash
# Code review with swarm agents
PR_DATA=$(gh pr view 123 --json files,additions,deletions,title,body)
PR_DIFF=$(gh pr diff 123)
npx ruv-swarm github review-init \
  --pr 123 --pr-data "$PR_DATA" --diff "$PR_DIFF" \
  --agents "security,performance,style,architecture" \
  --depth comprehensive

# Generate optimal CI/CD workflow
npx ruv-swarm actions generate-workflow \
  --analyze-codebase --detect-languages --create-optimal-pipeline

# Multi-repo coordination
npx claude-flow skill run github-multi-repo init \
  --repos "org/frontend,org/backend,org/shared" \
  --topology hierarchical --shared-memory
```

---

## 1. Code Review

### Multi-Agent Review System

Deploy specialized agents for parallel review:

```bash
npx ruv-swarm github review-init \
  --pr 123 \
  --agents "security,performance,style,architecture,accessibility" \
  --depth comprehensive
```

### Specialized Review Agents

| Agent | Focus | Checks |
|-------|-------|--------|
| **Security** | Vulnerabilities | SQL injection, XSS, auth bypasses, secret exposure, CORS |
| **Performance** | Optimization | Big O, query efficiency, memory patterns, cache, bundle size |
| **Architecture** | Design | SOLID, DRY, coupling, cohesion, circular deps |
| **Style** | Standards | Formatting, naming, docs, test coverage, error handling |
| **Accessibility** | a11y | WCAG compliance, ARIA, keyboard nav, screen readers |

### Label-Based Agent Assignment

```json
{
  "bug": ["debugger", "tester"],
  "feature": ["architect", "coder", "tester"],
  "refactor": ["analyst", "coder"],
  "performance": ["analyst", "optimizer"],
  "security": ["security", "authentication", "audit"]
}
```

### Quality Gates

```bash
npx ruv-swarm github quality-gates \
  --define '{
    "security": {"threshold": "no-critical"},
    "performance": {"regression": "<5%"},
    "coverage": {"minimum": "80%"},
    "architecture": {"complexity": "<10"}
  }'
```

### Review Configuration

```yaml
# .github/review-swarm.yml
version: 1
review:
  auto-trigger: true
  required-agents: [security, performance, style]
  optional-agents: [architecture, accessibility, i18n]
  thresholds:
    security: block
    performance: warn
    style: suggest
```

### PR Comment Commands

```markdown
/swarm init mesh 6
/swarm spawn coder "Implement authentication"
/swarm review --agents security,performance
/swarm status
```

---

## 2. Workflow Automation

### GitHub Actions Templates

#### Intelligent CI with Swarms

```yaml
# .github/workflows/swarm-ci.yml
name: Intelligent CI
on: [push, pull_request]
jobs:
  swarm-analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Initialize Swarm
        uses: ruvnet/swarm-action@v1
        with:
          topology: mesh
          max-agents: 6
      - name: Analyze Changes
        run: npx ruv-swarm actions analyze --commit ${{ github.sha }} --suggest-tests --optimize-pipeline
```

#### Auto-Review on PR Creation

```yaml
name: Automated Code Review
on:
  pull_request:
    types: [opened, synchronize]
jobs:
  swarm-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with: { fetch-depth: 0 }
      - run: echo "${{ secrets.GITHUB_TOKEN }}" | gh auth login --with-token
      - name: Run Review Swarm
        run: |
          PR_NUM=${{ github.event.pull_request.number }}
          REVIEW=$(npx ruv-swarm github review-all \
            --pr $PR_NUM \
            --pr-data "$(gh pr view $PR_NUM --json files,title,body,labels)" \
            --diff "$(gh pr diff $PR_NUM)" \
            --agents "security,performance,style,architecture")
          echo "$REVIEW" | gh pr review $PR_NUM --comment -F -
```

#### Self-Healing Pipeline

```yaml
name: Self-Healing Pipeline
on: workflow_run
jobs:
  heal-pipeline:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    steps:
      - name: Diagnose and Fix
        run: npx ruv-swarm actions self-heal --run-id ${{ github.event.workflow_run.id }} --auto-fix-common --create-pr-complex
```

### Workflow Analytics

```bash
# Performance analysis
npx ruv-swarm actions analytics --workflow "ci.yml" --period 30d --identify-bottlenecks --suggest-improvements

# Cost optimization
npx ruv-swarm actions cost-optimize --analyze-usage --suggest-caching --recommend-self-hosted

# Failure pattern detection
npx ruv-swarm actions failure-patterns --period 90d --classify-failures --suggest-preventions
```

---

## 3. Multi-Repo Coordination

### Cross-Repository Swarm Orchestration

```javascript
// Auto-discover related repositories
const REPOS = Bash(`gh repo list my-org --limit 100 \
  --json name,description,languages,topics \
  --jq '.[] | select(.languages | keys | contains(["TypeScript"]))'`)

mcp__claude-flow__swarm_init({
  topology: "hierarchical",
  maxAgents: 8,
  metadata: { repos: REPOS }
})
```

### Package Synchronization

```bash
npx claude-flow skill run github-multi-repo sync \
  --packages "claude-code-flow,ruv-swarm" \
  --align-versions --update-docs
```

### Organization-Wide Operations

```bash
# Dependency updates across all repos
npx claude-flow skill run github-multi-repo lib-update \
  --library "org/shared-lib" --version "2.0.0" \
  --find-consumers --update-imports --run-tests

# Security patches
npx claude-flow skill run github-multi-repo org-policy \
  --policy "add-security-headers" --repos "org/*" \
  --validate-compliance --create-reports
```

### Multi-Repo Config

```yaml
# .swarm/multi-repo.yml
version: 1
organization: my-org
repositories:
  - name: frontend
    role: ui
    agents: [coder, designer, tester]
  - name: backend
    role: api
    agents: [architect, coder, tester]
  - name: shared
    role: library
    agents: [analyst, coder]
coordination:
  topology: hierarchical
  communication: webhook
  memory: redis://shared-memory
```

### Synchronization Strategies

| Strategy | Use Case | Config |
|----------|----------|--------|
| **Eventual** | Docs, non-critical | `max-lag: 5m`, retry with backoff |
| **Strong** | Security, deps | `consensus: raft`, `quorum: 0.51` |
| **Hybrid** | Mixed workloads | Strong for security, eventual for docs |

---

## 4. Claude-Flow Integration

### Swarm Coordination Pattern

```javascript
[Single Message - Parallel Execution]:
  mcp__claude-flow__swarm_init { topology: "hierarchical", maxAgents: 5 }
  mcp__claude-flow__agent_spawn { type: "reviewer", name: "Senior Reviewer" }
  mcp__claude-flow__agent_spawn { type: "tester", name: "QA Engineer" }
  mcp__claude-flow__agent_spawn { type: "coordinator", name: "Merge Coordinator" }

  Bash("gh pr create --title 'Feature: Add authentication' --base main")
  Bash("npm test && npm run lint && npm run build")

  TodoWrite { todos: [
    { content: "Complete code review", status: "completed" },
    { content: "Run test suite", status: "completed" },
    { content: "Validate security", status: "in_progress" },
    { content: "Merge when ready", status: "pending" }
  ]}
```

---

## Security Best Practices

1. GitHub tokens scoped to minimal required permissions
2. Webhook signatures verified on all handlers
3. Command injection protection on PR comment commands
4. Rate limiting configured for all API operations
5. Audit logging enabled for swarm operations
6. Secrets scanning active, branch protection enforced

---

## Troubleshooting

```bash
# Review agents not spawning
npx ruv-swarm swarm-status
gh auth status
npx ruv-swarm github review-init --pr 123 --force

# Workflow failure analysis
gh run view <run-id> --json jobs,conclusion | npx ruv-swarm actions analyze-failure --suggest-fixes

# Multi-repo sync issues
npx claude-flow skill run github-multi-repo diagnose-connectivity --test-all-repos --check-permissions
```

---

## NTXP Interop

This skill participates in the NTXP shared ecosystem. Follow these conventions (see NTXP IPDM skill for full spec):

- **Knowledge Base**: Search `.ntxp/ipdm/project.yaml` and `.ntxp/coda/registry.yaml` before external calls. Save outputs back to `.ntxp/ipdm/project.yaml`.
- **Credentials**: Auth via `ntxp-id` plugin → secrets via `anthropic-skills:ntxp-secrets-vault` → never hardcode.
- **Model Routing**: Read `.ntxp/ipdm/model-council.yaml` for model config. Call `ntxp-model-council` if missing.
- **Skill Bindings**: Check `.ntxp/ipdm/skill-config.yaml` for read/write path declarations.
- **Platform Keys**: Use `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot` — no aliases.
