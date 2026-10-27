---
name: "GitHub Project Ops"
description: "Unified GitHub project operations: project board management, release orchestration, issue tracking, and sprint coordination with swarm automation. Use for project boards, release workflows, changelog generation, and deployment coordination."
---

# GitHub Project Ops

Unified skill combining project management, release orchestration, and issue tracking. Replaces the standalone `github-project-management` and `github-release-management` skills.

## Quick Start

```bash
# Issue management with swarm
gh issue create --title "Feature: Auth System" --body "..." --label "enhancement,swarm-ready"
npx ruv-swarm github issue-init 456 --topology mesh --auto-decompose --assign-agents "architect,coder,tester"

# Project board setup
PROJECT_ID=$(gh project list --owner @me --format json | jq -r '.projects[0].id')
npx ruv-swarm github board-init --project-id "$PROJECT_ID" --sync-mode "bidirectional"

# Release orchestration
gh release create v2.0.0 --draft --generate-notes --title "Release v2.0.0"
npx claude-flow github release-create --version "2.0.0" --build-artifacts --deploy-targets "npm,docker,github"
```

---

## 1. Issue Management

### Automated Issue Triage

```bash
# Triage unlabeled issues
npx ruv-swarm github triage --unlabeled --analyze-content --suggest-labels --assign-priority

# Find and link duplicates
npx ruv-swarm github find-duplicates --threshold 0.8 --link-related --close-duplicates
```

### Issue-to-Swarm Conversion

```bash
ISSUE_DATA=$(gh issue view 456 --json title,body,labels,assignees,comments)
npx ruv-swarm github issue-to-swarm 456 --issue-data "$ISSUE_DATA" --auto-decompose --assign-agents

# Batch process swarm-ready issues
ISSUES=$(gh issue list --label "swarm-ready" --json number,title,body,labels)
npx ruv-swarm github issues-batch --issues "$ISSUES" --parallel
```

### Task Decomposition

```bash
# Break down into subtasks
SUBTASKS=$(npx ruv-swarm github issue-decompose 456 --body "$(gh issue view 456 --json body --jq '.body')" --max-subtasks 10 --assign-priorities)

# Create linked issues for major subtasks
echo "$SUBTASKS" | jq -r '.tasks[] | select(.priority == "high")' | while read -r task; do
  gh issue create --title "$(echo "$task" | jq -r '.title')" --body "$(echo "$task" | jq -r '.description')\n\nParent: #456" --label "subtask"
done
```

### Issue Comment Commands

```markdown
/swarm analyze
/swarm decompose 5
/swarm assign @agent-coder
/swarm estimate
/swarm start
```

### Auto-Label Rules

```json
{
  "rules": [
    { "keywords": ["bug", "error", "broken"], "labels": ["bug"], "agents": ["debugger", "tester"] },
    { "keywords": ["feature", "implement", "add"], "labels": ["enhancement"], "agents": ["architect", "coder", "tester"] },
    { "keywords": ["slow", "performance"], "labels": ["performance"], "agents": ["analyst", "optimizer"] }
  ]
}
```

---

## 2. Project Board Automation

### Board Configuration

```yaml
# .github/board-sync.yml
version: 1
project:
  name: "AI Development Board"
mapping:
  status:
    pending: "Backlog"
    assigned: "Ready"
    in_progress: "In Progress"
    review: "Review"
    completed: "Done"
    blocked: "Blocked"
  agents:
    coder: "Development"
    tester: "Testing"
    analyst: "Analysis"
    architect: "Architecture"
  priority:
    critical: "Critical"
    high: "High"
    medium: "Medium"
    low: "Low"
```

### Smart Card Operations

```bash
# Auto-assign based on expertise and workload
npx ruv-swarm github board-auto-assign --strategy "load-balanced" --consider "expertise,workload,availability"

# Intelligent state transitions
npx ruv-swarm github board-smart-move --rules '{
  "auto-progress": "when:all-subtasks-done",
  "auto-review": "when:tests-pass",
  "auto-done": "when:pr-merged"
}'

# Multi-board sync
npx ruv-swarm github multi-board-sync --boards "Development,QA,Release" --sync-rules '{
  "Development->QA": "when:ready-for-test",
  "QA->Release": "when:tests-pass"
}'
```

### Sprint Management

```bash
# Sprint coordination
npx ruv-swarm github sprint-manage --sprint "Sprint 23" --auto-populate --capacity-planning --track-velocity

# Standup automation
npx ruv-swarm github standup-report --team "frontend" --include "yesterday,today,blockers" --format "slack"

# Milestone tracking
npx ruv-swarm github milestone-track --milestone "v2.0 Release" --update-board --show-dependencies --predict-completion
```

---

## 3. Release Orchestration

### Release Swarm Initialization

```javascript
[Single Message - Swarm Initialization]:
  mcp__claude-flow__swarm_init { topology: "hierarchical", maxAgents: 6 }
  mcp__claude-flow__agent_spawn { type: "coordinator", name: "Release Director" }
  mcp__claude-flow__agent_spawn { type: "coder", name: "Version Manager" }
  mcp__claude-flow__agent_spawn { type: "tester", name: "QA Engineer" }
  mcp__claude-flow__agent_spawn { type: "reviewer", name: "Release Reviewer" }
  mcp__claude-flow__agent_spawn { type: "analyst", name: "Deployment Analyst" }
```

### Changelog Generation

```bash
LAST_TAG=$(gh release list --limit 1 --json tagName -q '.[0].tagName')
PRS=$(gh pr list --state merged --base main --json number,title,labels,author,mergedAt \
  --jq ".[] | select(.mergedAt > \"$(gh release view $LAST_TAG --json publishedAt -q .publishedAt)\")")
COMMITS=$(gh api repos/:owner/:repo/compare/${LAST_TAG}...HEAD --jq '.commits[].commit.message')

npx claude-flow github changelog \
  --prs "$PRS" --commits "$COMMITS" \
  --from "$LAST_TAG" --to HEAD \
  --categorize --add-migration-guide
```

### Multi-Platform Deployment

```bash
# Build and deploy to multiple targets
npx claude-flow github release-build --platforms "linux,macos,windows" --architectures "x64,arm64" --parallel

npx claude-flow github release-deploy \
  --targets "npm,docker,github,s3" --staged-rollout --monitor-metrics --auto-rollback
```

### Progressive Deployment

```yaml
# .github/release-deployment.yml
deployment:
  strategy: progressive
  stages:
    - name: canary
      percentage: 5
      duration: 1h
      metrics: [error-rate < 0.1%, latency-p99 < 200ms]
      auto-advance: true
    - name: partial
      percentage: 25
      duration: 4h
      approval: qa-team
    - name: full
      percentage: 100
      approval: release-manager
      rollback-enabled: true
```

### Multi-Package Release

```javascript
[Single Message - Multi-Package Release]:
  mcp__claude-flow__swarm_init { topology: "mesh", maxAgents: 8 }
  Task("Package A Manager", "Release claude-flow v1.0.72", "coder")
  Task("Package B Manager", "Release ruv-swarm v1.0.12", "coder")
  Task("Integration Tester", "Validate cross-package compat", "tester")
  Task("Version Coordinator", "Align deps and versions", "coordinator")
```

### Emergency Hotfix

```bash
npx claude-flow github emergency-release \
  --issue 789 --severity critical --target-version v1.2.4 \
  --cherry-pick-commits --bypass-checks security-only --fast-track --notify-all
```

### Release Config

```yaml
# .github/release-swarm.yml
release:
  versioning:
    strategy: semantic
    breaking-keywords: ["BREAKING", "BREAKING CHANGE", "!"]
  changelog:
    sections:
      - { title: "Features", labels: [feature, enhancement] }
      - { title: "Bug Fixes", labels: [bug, fix] }
      - { title: "Breaking Changes", labels: [breaking], highlight: true }
      - { title: "Security", labels: [security], priority: critical }
  validation:
    pre-release: [lint, typecheck, unit-tests, integration-tests, security-scan]
    post-release: [smoke-tests, deployment-validation, performance-baseline]
  rollback:
    auto-rollback:
      triggers: [error-rate > 5%, latency-p99 > 2000ms, availability < 99%]
      grace-period: 5m
```

---

## 4. GitHub Actions Workflows

### Issue Swarm Handler

```yaml
name: Issue Swarm Handler
on:
  issues:
    types: [opened, labeled]
jobs:
  swarm-process:
    runs-on: ubuntu-latest
    steps:
      - name: Process Issue
        run: |
          if [[ "${{ github.event.label.name }}" == "swarm-ready" ]]; then
            npx ruv-swarm github issue-init ${{ github.event.issue.number }}
          fi
```

### Intelligent Release Workflow

```yaml
name: Intelligent Release
on:
  push:
    tags: ['v*']
jobs:
  release:
    runs-on: ubuntu-latest
    permissions: { contents: write, packages: write, issues: write }
    steps:
      - uses: actions/checkout@v3
        with: { fetch-depth: 0 }
      - uses: actions/setup-node@v3
        with: { node-version: '20', cache: 'npm' }
      - run: echo "${{ secrets.GITHUB_TOKEN }}" | gh auth login --with-token
      - name: Build, Test, Release
        run: |
          npm ci && npm run lint && npm run test:all && npm run build
          npx claude-flow@alpha github changelog --categorize --add-migration-guide > CHANGELOG.md
          gh release edit ${{ github.ref_name }} --notes "$(cat CHANGELOG.md)" --draft=false
          for file in dist/*; do gh release upload ${{ github.ref_name }} "$file"; done
          npm publish
```

---

## Issue Templates

### Swarm Task Template

```yaml
# .github/ISSUE_TEMPLATE/swarm-task.yml
name: Swarm Task
body:
  - type: dropdown
    id: topology
    attributes:
      label: Swarm Topology
      options: [mesh, hierarchical, ring, star]
  - type: input
    id: agents
    attributes:
      label: Required Agents
      placeholder: "coder, tester, analyst"
  - type: textarea
    id: tasks
    attributes:
      label: Task Breakdown
```

---

## Analytics & Metrics

```bash
# Board KPIs
npx ruv-swarm github board-kpis --metrics '["average-cycle-time","throughput-per-sprint","blocked-time-percentage"]'

# Release analytics
npx claude-flow github release-analytics --version v2.0.0 --compare-with v1.9.0 --metrics "adoption,performance,stability"

# Issue metrics
npx ruv-swarm github issue-metrics --issue 456 --metrics "time-to-close,agent-efficiency,subtask-completion"

# Swarm effectiveness
npx ruv-swarm github effectiveness --issues "closed:>2024-01-01" --compare "with-swarm,without-swarm"
```

---

## Best Practices

1. **Issues**: Initialize swarm for complex issues, assign specialized agents by type, use memory for coordination
2. **Boards**: Clear column definitions, systematic labeling, regular grooming, well-defined automation rules
3. **Releases**: Strict semver, code freeze 3 days before, beta testing for majors, stakeholder communication
4. **Deployment**: Canary first, staged rollouts with monitoring, automated health checks, quick rollback
5. **Security**: Validate commands before execution, rate limit operations, audit all swarm actions

---

## Troubleshooting

```bash
# Board sync issues
npx ruv-swarm github board-diagnose --check "permissions,webhooks,rate-limits" --test-sync

# Release build failures
npx claude-flow@alpha diagnostic-run --component build --verbose

# Version conflicts
npx claude-flow@alpha github release-validate --checks version-conflicts --auto-resolve

# Rollback
npx claude-flow@alpha github rollback --to-version v1.9.9 --reason "Critical bug" --preserve-data --notify-users
```

---

## NTXP Interop

This skill participates in the NTXP shared ecosystem. Follow these conventions (see NTXP IPDM skill for full spec):

- **Knowledge Base**: Search `.ntxp/ipdm/project.yaml` and `.ntxp/coda/registry.yaml` before external calls. Save outputs back to `.ntxp/ipdm/project.yaml`.
- **Credentials**: Auth via `ntxp-id` plugin → secrets via `anthropic-skills:ntxp-secrets-vault` → never hardcode.
- **Model Routing**: Read `.ntxp/ipdm/model-council.yaml` for model config. Call `ntxp-model-council` if missing.
- **Skill Bindings**: Check `.ntxp/ipdm/skill-config.yaml` for read/write path declarations.
- **Platform Keys**: Use `google_drive`, `ebuilder`, `jobtread`, `building_connected`, `procore`, `hubspot` — no aliases.
