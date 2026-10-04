# Testing, Evals and Acceptance

## Verification protocol (required for every task)
1. /start-task passes the dependency gate.
2. Write scripts/verify/T-xxx.(py|sh|spec.ts). It must assert results, cover each acceptance criterion below, and include one negative case.
3. Run `python3 scripts/verify/run.py T-xxx`. It saves a log in docs/verification-logs/ and appends a row to docs/VERIFICATION.md with a SHA256 of the log.
4. Only PASS allows /finish-task. A later FAIL cancels an earlier PASS.
5. Manual-only checks use `--manual`, run by a human in a real terminal.

## Tool per layer
| What | Tool |
|---|---|
| Rules, parsers, redaction, schemas | pytest |
| FastAPI endpoints, webhook (signed fixture payload) | pytest + httpx or curl |
| Database, migrations, pgvector | psql or pytest against docker db |
| Dashboard and the three gates | Playwright (`.spec.ts`), Playwright MCP to explore |
| Postman collection runner | Newman, check exit code and JSON report |
| Playwright runner against staging | run a known pass, known fail, and an undeployed endpoint |
| Agents | eval set (20-30 cases) + schema validity + retry cap behavior |
| GitHub / Jira | mocked first, then one real call on the test repo and test project, clean up after |
| Full loop | Playwright e2e on the demo repo + staging app |

## Test layers
- Unit (pytest, vitest): rules, parsers, redaction, schema validation
- Integration: webhook -> analysis, runner -> evidence, approval -> Jira (mocked and one real)
- Agent evals: 20-30 labeled cases per agent in tests/evals/<agent>/
- End to end: full loop on the demo repo and staging app

## Acceptance criteria per deliverable
| Deliverable | Accept when |
|---|---|
| D1 Connect + upload | Connecting repo creates webhook automatically; bad spec shows an error in preview before import |
| D2 Risk scoring | Label appears for a new PR; new-module PR scored by size; eval accuracy recorded |
| D3 Test run + gap drafting | One click runs UI + API; undeployed target is deployment_pending; timeout retried once; drafted test compiles |
| D4 Evidence | Screenshot, trace and logs visible per failed test |
| D5 Report + Jira | Ticket cites log lines, secrets removed, nothing filed without approval, Jira key stored |
| Loop | PR -> ticket works end to end in the demo |

## Eval log
Append results here (date, agent, model, n cases, accuracy, schema validity, latency, notes).

| Date | Agent | Model | Cases | Accuracy | Valid schema | Latency | Notes |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Safety checks to test explicitly
- Retry cap stops at limit and escalates
- deployment_pending never reaches Report Agent
- Secret fixtures never appear in output
- Disagreement between two judgment runs routes to human
