# Contributions

Ownership by area. Task-level status is in BACKLOG.md. Lead writes code, Support reviews the PR. Both approve shared-schema changes.

## Ownership
| Area | Farheen | Arisha |
|---|---|---|
| Orchestration (ADK graph, session state, pause/resume) | Lead | Support |
| Manager Agent | Lead | Support |
| Analysis Agent (scoring, size-based new-module logic, votes) | Lead | |
| Module defect history query + Analysis eval set (QA labelling) | Support | Lead |
| GitHub PR diff fetch | Support | Lead |
| Test Agent: test selection | Lead | Support |
| Test Agent: runners (Playwright, Newman) | Support | Lead |
| Test Agent: deployment_pending + failure classification + eval | Support | Lead |
| Test Agent: coverage gap detection + drafting + gate 2 | Lead | Support |
| Gate 1 (Run Now) and gate 3 (ticket approval + Jira filing) | Support | Lead |
| Evidence capture, trace viewer, results screen | Support | Lead |
| Evidence storage + evidence bundler for Report Agent | Lead | Support |
| Secret redaction | Lead | Support |
| Report Agent (root cause, ticket) | Lead | |
| LLM router, ADK + non-Gemini spike, model evals, final model choice | Lead | Support |
| Database and migrations | Lead | Support |
| FastAPI scaffold, routes, CI, repo setup, staging app | Support | Lead |
| GitHub OAuth, webhook, Jira connect | Support | Lead |
| Test Library parsing and storage | Support | Lead |
| Upload widget with live preview | Lead | Support |
| Dashboard screens (other than above) | Support | Lead |
| Docs, demo, thesis | Both | Both |

## FYP-II
| Feature | Lead | Support |
|---|---|---|
| QA Memory | Farheen | Arisha |
| Suggest a Fix | Farheen | Arisha |
| Regression Comparison | Arisha | Farheen |
| Cross-PR Risk Trends | Arisha | Farheen |

## Fairness check (effort weighted, not task count)
Each task has a size: small = 1, medium = 2, large = 3 (QA Memory = 4). Lead gets full weight, Support gets 30%, shared tasks split 50/50.

| Scope | Farheen | Arisha |
|---|---|---|
| FYP-I | 62.7 (49%) | 64.8 (51%) |
| FYP-II | 10.3 (52%) | 9.6 (48%) |
| Whole year | 73.0 (49.5%) | 74.4 (50.5%) |

Per phase the gap stays under 4 points, except D3 (Arisha +3.3, 3 weeks long) and D5 (Farheen +2.3). Farheen carries more reasoning and eval work, Arisha more integration and UI work.

Re-run this check when tasks move. If either person is more than 5 points behind or ahead over a phase, rebalance in BACKLOG.md and log it in DECISIONS.md.

## Rules
- Changing a shared schema (agent I/O, DB tables): tell the other person first.
- Ownership changes are recorded here and in DECISIONS.md.
