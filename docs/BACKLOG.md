# Backlog

Single source of truth for tasks. Status: TODO | IN PROGRESS | IN REVIEW | BLOCKED | DONE.
DONE = merged, tests pass, docs updated (see CONTRIBUTING.md). Update with /end-session.
Dep = task that must be DONE **and verified** first. Claude Code blocks work on a task whose Dep is unfinished (see CLAUDE.md, dependency gate).
Never set DONE by hand: use /finish-task after a PASS in docs/VERIFICATION.md.
**Version 1.0 = FYP-1 COMPLETE** = every FYP-1 task (T-001 to T-092) DONE and verified. T-093 is RECURRING and does not count. FYP-2 tasks (T-100+) stay locked until v1.0. Progress: `python3 .claude/hooks/version_status.py` or /version.

Last updated: 2026-10-04
Weights used for the fairness check are in CONTRIBUTIONS.md.

## Phase 0: Proposal (wk 1-2)
| ID | Task | Lead | Support | Dep | Status |
|---|---|---|---|---|---|
| T-001 | Proposal written and submitted | Both | | | DONE |
| T-002 | Claude Code project docs set up (CLAUDE.md, docs, .claude) | Farheen | Arisha | T-001 | IN PROGRESS |

## Phase 1: Environment (wk 3-4)
| ID | Task | Lead | Support | Dep | Status |
|---|---|---|---|---|---|
| T-010 | Repo init, layout, branch protection | Arisha | Farheen | T-002 | TODO |
| T-011 | PostgreSQL + pgvector via docker compose | Farheen | Arisha | T-010 | TODO |
| T-012 | Initial schema and migrations (DATA_MODEL.md) | Farheen | Arisha | T-011 | TODO |
| T-013 | FastAPI scaffold, health route, config loading | Arisha | Farheen | T-010 | TODO |
| T-014 | Register GitHub OAuth App | Arisha | | | TODO |
| T-015 | Create Jira Cloud project and API token | Arisha | | | TODO |
| T-016 | ADK skeleton, hello agent, session state in Postgres | Farheen | | T-011 | TODO |
| T-017 | Spike: ADK with Groq and OpenRouter models (LiteLLM or wrapper) | Farheen | | T-016 | TODO |
| T-018 | Choose and deploy demo staging app and test repo | Arisha | Farheen | | TODO |
| T-019 | CI: lint, type check, tests on PR | Arisha | | T-010 | TODO |

## Phase 2: D1 Connect + upload, plus agent core (wk 5-6)
| ID | Task | Lead | Support | Dep | Status |
|---|---|---|---|---|---|
| T-020 | GitHub + Jira login flow (one login) | Arisha | Farheen | T-014, T-015 | TODO |
| T-021 | Automatic webhook provisioning | Arisha | | T-020 | TODO |
| T-022 | Webhook receiver with signature verification | Arisha | Farheen | T-013 | TODO |
| T-023 | Parser for TS Playwright specs and Postman collection | Arisha | | T-013 | TODO |
| T-024 | Upload widget with live preview | Farheen | Arisha | T-023 | TODO |
| T-025 | Test Library storage and listing | Arisha | | T-012, T-023 | TODO |
| T-026 | LLM router, config.yaml, fallback, model_calls logging | Farheen | | T-017 | TODO |
| T-035 | Manager Agent: validation, retry cap, escalation | Farheen | Arisha | T-016 | TODO |

## Phase 3: D2 Risk scoring (wk 7-8)
| ID | Task | Lead | Support | Dep | Status |
|---|---|---|---|---|---|
| T-030 | GitHub PR diff fetch via integration | Arisha | Farheen | T-022 | TODO |
| T-031 | Analysis Agent: rule-based risk score | Farheen | | T-030, T-026 | TODO |
| T-032 | Module defect history query | Arisha | Farheen | T-012 | TODO |
| T-033 | New-module size-based scoring | Farheen | | T-031 | TODO |
| T-034 | Yes/no risk questions + majority vote of 3 | Farheen | | T-031 | TODO |
| T-036 | PR and risk dashboard screen | Arisha | Farheen | T-031 | TODO |
| T-037 | Analysis eval set (20-30 cases) | Arisha | Farheen | T-031 | TODO |

## Phase 4: D3 Test execution + gap drafting (wk 9-11)
| ID | Task | Lead | Support | Dep | Status |
|---|---|---|---|---|---|
| T-040 | Test selection from risk output | Farheen | Arisha | T-031, T-025 | TODO |
| T-041 | Playwright runner (subprocess, timeout) | Arisha | Farheen | T-018 | TODO |
| T-042 | Newman runner | Arisha | | T-018 | TODO |
| T-043 | deployment_pending check | Arisha | | T-041 | TODO |
| T-044 | Failure classification (rules first, model for ambiguous) | Arisha | Farheen | T-041, T-026 | TODO |
| T-045 | Timeout retry once | Arisha | | T-044 | TODO |
| T-046 | Run Now endpoint, button, ADK pause/resume (gate 1) | Arisha | Farheen | T-041, T-042 | TODO |
| T-047 | Coverage gap detection | Farheen | Arisha | T-040 | TODO |
| T-048 | Draft Playwright/Postman tests + TS compile check | Farheen | Arisha | T-047 | TODO |
| T-049 | Approve drafted tests: backend and UI (gate 2) | Farheen | Arisha | T-048 | TODO |
| T-050 | Test Agent eval set: selection + classification | Arisha | Farheen | T-044 | TODO |
| T-051 | Test Agent eval set: drafting | Farheen | Arisha | T-048 | TODO |

## Phase 5: D4 Evidence, plus redaction (wk 12-13)
| ID | Task | Lead | Support | Dep | Status |
|---|---|---|---|---|---|
| T-060 | Capture screenshots, traces, console/network logs | Arisha | | T-041 | TODO |
| T-061 | Evidence storage on disk, paths in DB | Farheen | Arisha | T-060 | TODO |
| T-062 | Results and evidence screen | Arisha | Farheen | T-061 | TODO |
| T-063 | Playwright Trace Viewer integration | Arisha | | T-060 | TODO |
| T-064 | Evidence bundler: trim and package logs per failure as Report Agent input | Farheen | Arisha | T-061 | TODO |
| T-070 | Secret redaction with tests | Farheen | Arisha | T-012 | TODO |

## Phase 6: D5 Report + Jira (wk 14-15)
| ID | Task | Lead | Support | Dep | Status |
|---|---|---|---|---|---|
| T-071 | Report Agent: root cause with log citations | Farheen | | T-070, T-026 | TODO |
| T-072 | Ticket schema and draft | Farheen | Arisha | T-071 | TODO |
| T-073 | Jira filing via integration + fallback interface | Arisha | Farheen | T-015 | TODO |
| T-074 | Ticket approval: backend and UI (gate 3) | Arisha | Farheen | T-072 | TODO |
| T-075 | Report Agent eval set | Farheen | Arisha | T-071 | TODO |

## Phase 7: Integration + demo (wk 16)
| ID | Task | Lead | Support | Dep | Status |
|---|---|---|---|---|---|
| T-080 | End-to-end test of full loop | Both | | all above | TODO |
| T-081 | Documentation and thesis draft | Both | | T-080 | TODO |
| T-082 | Demo script and rehearsal | Both | | T-080 | TODO |

## Cross-cutting
| ID | Task | Lead | Support | Dep | Status |
|---|---|---|---|---|---|
| T-090 | Final model choice per agent from eval results | Farheen | Arisha | T-037, T-050, T-051, T-075 | TODO |
| T-091 | Align proposal 5.2 with chosen models | Farheen | | T-090 | TODO |
| T-092 | Confirm three gates with supervisor | Both | | | TODO |
| T-093 | Weekly Friday review of STATUS and RISKS | Both | | | RECURRING |

## FYP-II (LOCKED until FYP-1 IS COMPLETED, version 1.0)
| ID | Task | Lead | Support | Wk | Status |
|---|---|---|---|---|---|
| T-100 | QA Memory (embeddings + pgvector recall) | Farheen | Arisha | 17-20 | TODO |
| T-110 | Suggest a Fix | Farheen | Arisha | 21-24 | TODO |
| T-120 | Regression Comparison | Arisha | Farheen | 25-27 | TODO |
| T-130 | Cross-PR Risk Trend Reporting | Arisha | Farheen | 28-30 | TODO |
| T-140 | Final testing, thesis docs, final demo | Both | | 31-32 | TODO |
