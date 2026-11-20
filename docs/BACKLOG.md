# Backlog

Single source of truth for tasks. Status: TODO | IN PROGRESS | IN REVIEW | BLOCKED | DONE.
DONE = merged, tests pass, docs updated (see CONTRIBUTING.md). Update with /end-session.
Dep = task that must be DONE **and verified** first. Claude Code blocks work on a task whose Dep is unfinished (see CLAUDE.md, dependency gate).
Never set DONE by hand: use /finish-task after a PASS in docs/VERIFICATION.md.
**Version 1.0 = FYP-1 COMPLETE** = every FYP-1 task (T-001 to T-092) DONE and verified. T-093 is RECURRING and does not count. FYP-2 tasks (T-100+) stay locked until v1.0. Progress: `python3 .claude/hooks/version_status.py` or /version.

Last updated: 2026-11-14
Weights used for the fairness check are in CONTRIBUTIONS.md.

**2026-11-02 consolidation.** D1 (official_ui-main) and the completed part of D2 (multi-agents)
were merged into one working application in the `mid/` folder, with 190 passing tests. Tasks whose
code exists and passes tests there are set to **IN REVIEW**, not DONE: DONE needs a PASS row written
by `scripts/verify/run.py` in docs/VERIFICATION.md, and none of this work has one yet. Ownership is
unchanged. See "Consolidation status" below for exactly what was verified and what was not.

## Phase 0: Proposal (wk 1-2)
| ID | Task | Lead | Support | Dep | Status |
|---|---|---|---|---|---|
| T-001 | Proposal written and submitted | Both | | | DONE |
| T-002 | Claude Code project docs set up (CLAUDE.md, docs, .claude) | Farheen | Arisha | T-001 | DONE |

## Phase 1: Environment (wk 3-4)
| ID | Task | Lead | Support | Dep | Status |
|---|---|---|---|---|---|
| T-010 | Repo init, layout (branch protection dropped, D-008) | Arisha | Farheen | T-002 | DONE |
| T-011 | PostgreSQL + pgvector (Neon, D-009; docker compose kept as local fallback) | Farheen | Arisha | T-010 | DONE |
| T-012 | Initial schema and migrations (DATA_MODEL.md) | Farheen | Arisha | T-011 | DONE |
| T-013 | FastAPI scaffold, health route, config loading | Arisha | Farheen | T-010 | DONE |
| T-014 | Register GitHub OAuth App | Arisha | | | TODO |
| T-015 | Create Jira Cloud project and API token | Arisha | | | TODO |
| T-016 | ADK skeleton, hello agent, session state in Postgres | Farheen | | T-011 | DONE |
| T-017 | Spike: ADK with Groq and OpenRouter models (LiteLLM or wrapper) | Farheen | | T-016 | DONE |
| T-018 | Choose and deploy demo staging app and test repo | Arisha | Farheen | | TODO |
| T-019 | CI: lint, type check, tests on PR | Arisha | | T-010 | DONE |

## Phase 2: D1 Connect + upload, plus agent core (wk 5-6)
| ID | Task | Lead | Support | Dep | Status |
|---|---|---|---|---|---|
| T-020 | GitHub + Jira login flow (one login) | Arisha | Farheen | T-014, T-015 | IN REVIEW |
| T-021 | Automatic webhook provisioning | Arisha | | T-020 | IN REVIEW |
| T-022 | Webhook receiver with signature verification | Arisha | Farheen | T-013 | DONE |
| T-023 | Parser for TS Playwright specs and Postman collection | Arisha | | T-013 | IN REVIEW |
| T-024 | Upload widget with live preview | Farheen | Arisha | T-023 | IN REVIEW |
| T-025 | Test Library storage and listing | Arisha | | T-012, T-023 | IN REVIEW |
| T-026 | LLM router, config.yaml, fallback, model_calls logging | Farheen | | T-017 | DONE |
| T-035 | Manager Agent: validation, retry cap, escalation | Farheen | Arisha | T-016 | DONE |

## Phase 3: D2 Risk scoring (wk 7-8)
| ID | Task | Lead | Support | Dep | Status |
|---|---|---|---|---|---|
| T-030 | GitHub PR diff fetch via integration | Arisha | Farheen | T-022 | DONE |
| T-031 | Analysis Agent: rule-based risk score | Farheen | | T-030, T-026 | DONE |
| T-032 | Module defect history query | Arisha | Farheen | T-012 | DONE |
| T-033 | New-module size-based scoring | Farheen | | T-031 | DONE |
| T-034 | Yes/no risk questions + majority vote of 3 | Farheen | | T-031 | DONE |
| T-036 | PR and risk dashboard screen | Arisha | Farheen | T-031 | DONE |
| T-037 | Analysis eval set (20-30 cases) | Arisha | Farheen | T-031 | TODO |
| T-038 | PR file graph + per-file risk + past-log endpoints, live stage view (prompt §8, P-D8) | Arisha | Farheen | T-036 | DONE |
| T-039 | Manager judgment check: model asked twice if a claim is supported by evidence, disagreement -> human review (D-012) | Farheen | Arisha | T-035 | TODO |

### Consolidation status, 2026-11-02 (`mid/` folder)

What the code actually does, checked against both source folders and against 190 passing tests.
This section records evidence; it does not change any status above.

**Implemented and tested**
- T-031, T-033 — `mid/agents/risk_rules.py`, `mid/agents/analysis.py`. Rules decide the label
  (size + defect history + sensitive areas, then minimum labels); a module with no history is
  scored by change size. 24 unit tests in `mid/tests/test_risk_rules.py`.
- T-035 — `mid/agents/manager.py`. Validation in plain code, feedback retry, cap at 3 attempts,
  escalation to `needs_human_review`. The retry cap and escalation are asserted end to end, and a
  live run was accepted on the first attempt.
- T-030, T-032 — `mid/agents/github_client.py`. Verified against the real GitHub API: a live run on
  `psf/requests#6500` fetched the changed files and found 21 past bug-fix commits in the touched
  module, which moved the score to 5 (Medium).
- T-020 to T-025 — the D1 app, consolidated unchanged, with its own five test suites passing, plus
  a full pass of `scripts/check_database.py` against the shared Neon database (accounts, 2FA,
  connect, Test Library CRUD, cascading delete; the Test Agent's 8 runs / 195 results / 3 drafts
  fingerprinted unchanged).
- Webhook → agent → database → dashboard integration: 26 tests in
  `mid/tests/test_analysis_integration.py`, plus a live 20/20 pass of `mid/scripts/live_check.py`
  on the real Neon database with the real agent and a real model
  (`groq/openai/gpt-oss-20b`). A wrongly signed delivery is refused with 401 and never reaches the
  agent. The database held exactly its original rows afterwards.

None of this is DONE or WORKING yet: that needs a PASS row from `scripts/verify/run.py`, and the
per-task verification scripts (`scripts/verify/T-030.py` and friends) have not been written.

**Implemented but not fully tested**
- T-020 — email/password sign-in and 2FA are verified against real PostgreSQL, but the GitHub and
  Atlassian OAuth halves are not: `GITHUB_CLIENT_ID/SECRET` and `ATLASSIAN_CLIENT_ID/SECRET` are
  still placeholders in `mid/.env` (they were not in the multi-agents `.env`, and official_ui-main
  has no `.env` at all). Tested only with the OAuth calls faked.
- T-026 — a working model chain with per-task priority and skip-on-no-key exists in
  `mid/agents/llm.py`, but it is **not** the task as written: there is no `config.yaml` and no
  `model_calls` logging table. Left IN PROGRESS for that reason.
- T-016 — the ADK skeleton and the real manager/worker graph exist, but session state is held by
  `InMemorySessionService`, not Postgres, so runs do not survive a restart. IN PROGRESS.
- T-017 — the non-Gemini wrapper is real: `mid/agents/models.py` routes groq and openrouter through
  LiteLLM and strips the `reasoning_content` field Groq rejects. Never run against a live provider
  from the consolidated folder.
- T-011, T-012 — tables are created by SQLAlchemy `create_all` plus a small column-adding step, and
  pgvector is enabled on startup. There are no Alembic migrations, which T-012 asks for, and the
  docker compose database was not started. Both IN PROGRESS.
- T-021, T-022 — signature verification is verified live (correct signature accepted, wrong one
  refused with 401 before any processing). Webhook *creation* on a real repository is not: that
  needs the GitHub OAuth app and a running tunnel, so no delivery from github.com has reached the
  consolidated folder.

**Not implemented**
- T-034 — no yes/no risk questions and no majority vote of 3 anywhere in multi-agents. The agent
  makes one model call, for the explanation only, and the label never depends on it. Still TODO.
- T-036 — no PR or risk screen exists in official_ui-main; the rail shows "Pull Requests" as a
  disabled Coming Soon button and the only risk UI is the hardcoded marketing mockup on the landing
  page. `mid/frontend/src/dashboard/RiskView.tsx` is the integration needed to display the agent's
  output at all, built from the mockup's design. It is **not** a delivery of T-036, which stays
  TODO and Arisha's.
- T-037 — no eval set, so there is no recorded accuracy for the risk labels. docs/TESTING.md
  requires it before D2 can be accepted.

**Blocked by missing configuration**
- The GitHub and Atlassian OAuth client credentials are missing, so the one-login flow (T-020) and
  automatic webhook creation (T-021) cannot be exercised for real.
- The shared database already holds one account whose GitHub/Atlassian token and one whose two-step
  secret were encrypted under the *original* official_ui-main `SECRET_KEY` and
  `TOTP_ENCRYPTION_KEY`. Those keys were never committed and are not available, so `mid/.env` uses
  newly generated ones. That account must re-link GitHub and Atlassian and re-enrol two-step
  verification unless the original keys turn up. No row is damaged; the ciphertext is simply
  unreadable. Worth recording in DECISIONS.md.
- T-037 cannot start until someone labels 20-30 cases. The model side is no longer a blocker: a
  live Groq call succeeded from the consolidated folder.

**Out of scope, deliberately left alone**
- The Test & Execution Agent (`multi-agents/test_agent/`, `manager_agent/test_phase.py`) is still
  in its testing phase and belongs to Phase 4. It was not consolidated.

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
| T-094 | Persist analysis artifacts: PR file snapshots and agent run steps in Postgres, feed index, bounded agent cache (D-013) | Farheen | Arisha | T-038 | DONE |
| T-095 | Risk Analysis dashboard layout: view tabs at the top of the page, card grid (KPIs, charts, live log, PR table) like the reference dashboard, Verixa palette and header unchanged, saved backend data only (Farheen's layout prompt, 2026-11-15) | Farheen | Arisha | T-094 | DONE |
| T-096 | Pull Requests section first (every repo PR, author from GitHub saved in Neon via pull_requests table, search, expand), central live processing view from real agent events, tab data kept and cached (no refetch on tab switch or reload), multi-line test cells and Tests chips fixed, card transitions (Farheen's prompt, 2026-11-15) | Farheen | Arisha | T-095 | DONE |
| T-097 | UI consistency: landing page wording on dashboard cards, one shared card surface (landing + dashboard) with 3D depth like the reference screenshot, Analyses per day as its own full-width section with an expanding View as table, smooth chart/table transitions (Farheen's prompt, 2026-11-15) | Farheen | Arisha | T-096 | DONE |
| T-098 | Frontend refinements: frosted glass sliding indicator on the Risk view tabs; Live runs and logs Results and Tests laid out without empty space (Farheen's prompt, 2026-11-15) | Farheen | Arisha | T-097 | DONE |
| T-099 | Defect history shown as "No defect history" (not "Waiting") when a module has none, kept apart from the agent's run status; source and target branch of every pull request saved in Neon (pull_requests), Pull Requests filtered by branch in the API and the UI (Farheen's prompt, 2026-11-16) | Farheen | Arisha | T-098 | DONE |
| T-089 | Premium Risk screens: smooth two-series area chart on Overview like the reference (hover to compare), share rings on the risk tiles; pull request detail on the page background and Dependency graph on white in the light theme; each agent (Manager, Analysis, Test) gets its own animation in the live processing view with smooth transitions between them; Analysis stages follow the live socket, turn green one after another with an animated track, Defect history and CI grey when not covered (2026-11-21 prompt) | Arisha | Farheen | T-099 | IN PROGRESS |
| T-093 | Weekly Friday review of STATUS and RISKS | Both | | | RECURRING |

## FYP-II (LOCKED until FYP-1 IS COMPLETED, version 1.0)
| ID | Task | Lead | Support | Wk | Status |
|---|---|---|---|---|---|
| T-100 | QA Memory (embeddings + pgvector recall) | Farheen | Arisha | 17-20 | TODO |
| T-110 | Suggest a Fix | Farheen | Arisha | 21-24 | TODO |
| T-120 | Regression Comparison | Arisha | Farheen | 25-27 | TODO |
| T-130 | Cross-PR Risk Trend Reporting | Arisha | Farheen | 28-30 | TODO |
| T-140 | Final testing, thesis docs, final demo | Both | | 31-32 | TODO |
