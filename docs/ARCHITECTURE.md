# Architecture

## Pattern
Supervisor / orchestrator-worker. One Manager Agent over three workers, built with Google ADK. ADK session service saves state after every step so runs resume after a crash.

## Flow
GitHub webhook (PR opened/updated)
-> Analysis Agent (automatic) -> risk label
-> GATE 1: tester clicks Run Now
-> Test Agent: select tests, run Playwright + Newman, classify failures, draft tests for gaps
-> GATE 2: tester approves drafted test cases
-> Report Agent: root cause hypothesis + ticket draft
-> GATE 3: tester approves ticket -> filed to Jira
Manager validates after each worker. Invalid output -> retry with feedback (capped) -> human review.

Note: proposal text says two gates (run, file). The proposal diagram also shows test-case approval, so we treat it as a third gate. Confirm with supervisor.

## Agents
**Manager**: assigns tasks, validates schema and evidence, caps retries, escalates. Validation is plain code. A judgment check ("is this claim supported by evidence?") may use a small model.

**Analysis**: reads PR diff via GitHub integration. Risk from files changed, module touched, module defect history. If the module has no history, score from change size (files + lines), not a fixed default.

**Test**: picks relevant Playwright tests and the Newman collection, runs on staging. Target not on staging -> `deployment_pending`. Failure -> `real_bug` | `timeout` (retry once) | `deployment_pending`. Drafts tests for coverage gaps.

**Report**: correlates screenshots, traces, console/network logs into a root cause hypothesis, redacts secrets, drafts the Jira ticket, waits for approval.

## Run states
`pr_received -> risk_scored -> awaiting_run -> running -> results_ready -> awaiting_test_approval -> reporting -> awaiting_ticket_approval -> filed | escalated | failed`

## Data
PostgreSQL + pgvector: ADK session state, PRs, risk, test runs, Jira links, later embeddings. Raw evidence on disk, paths in DB. See DATA_MODEL.md.

## Integrations
See INTEGRATIONS.md.

## Backend / Frontend
FastAPI exposes REST + WebSocket. One backend, one run object, one evidence store. React + TS dashboard, minimal screens.

## Repo layout
```
verixa/
  CLAUDE.md  README.md  CONTRIBUTING.md  CHANGELOG.md  .env.example
  .claude/        settings.json, commands/, agents/
  docs/           all project docs, sessions/
  backend/
    agents/        manager.py analysis.py test.py report.py
    llm/           router.py config.yaml
    integrations/  github.py jira.py playwright.py newman.py
    api/           routes, websocket
    db/            models, migrations
    evidence/      redaction.py storage.py
  frontend/        React + TS
  tests/           unit, integration, evals/<agent>/
  data/            evidence files (gitignored)
```
