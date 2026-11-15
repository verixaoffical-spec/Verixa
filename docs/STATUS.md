# Project Status

Last updated: 2026-11-14 by: Farheen (via Claude)
Version: v0.0 (FYP-1 in progress). **v1.0 = FYP-1 COMPLETE.** Check with /version.
Phase: D1 built, D2 risk scoring built and consolidated. Next: a verification run with real
credentials, then the T-037 eval set.

## State legend
- NOT STARTED
- IN PROGRESS
- BUILT, UNVERIFIED : code exists, not yet run end to end
- WORKING : verified by scripts/verify/run.py with a PASS row in docs/VERIFICATION.md. Record date and command.
- BROKEN : was working or built, now failing. Add note.

## Consolidation, 2026-11-02

D1 and the completed part of D2 now live as one working application in the **`mid/`** folder,
outside this repository. The two source folders (`official_ui-main`, `multi-agents`) were treated
as read-only and are byte-identical to before the merge (SHA256 over 87 and 40 files).

Nothing is marked WORKING below, because **WORKING needs a PASS row in docs/VERIFICATION.md** and
no verification script has been run for any of this work. "BUILT, UNVERIFIED" here is stronger than
usual: the code exists, has 190 passing tests of its own, and has been exercised live against the
shared Neon database, the real GitHub API and a real model — it simply has not been through
`scripts/verify/run.py`. Writing `scripts/verify/T-0xx.py` for T-030 to T-033 and T-035 is the next
step, and most of the assertions can be lifted from `mid/tests/` and `mid/scripts/live_check.py`.

Live checks run on 2026-11-02 from `mid/`:
- `python -m unittest tests.*` — 190 passed (SQLite)
- `python -m scripts.check_database` — all checks passed on the shared Neon database; the Test
  Agent's 8 runs / 195 results / 3 drafts fingerprinted unchanged
- `python scripts/live_check.py` — 20/20 passed: signed webhook -> Analysis Agent -> Neon ->
  dashboard API, then cleaned up. Wrong signature refused with 401 before any processing
- a live analysis of `psf/requests#6500`: rules scored it Medium (5) using 21 real bug-fix commits
  found in the touched module, and `groq/openai/gpt-oss-20b` wrote the reasoning and five test
  areas, accepted by the Manager on attempt 1

## Feature status (FYP-I)
| Feature | State | Tasks | Last verified | Verify with | Notes |
|---|---|---|---|---|---|
| Repo layout + mid import | WORKING | T-010 | 2026-11-14 | `python3 scripts/verify/run.py T-010` | 169 mid files byte-identical, 455 tests pass, frontend builds. Branch protection dropped (D-008) |
| Database: Neon PostgreSQL 18 + pgvector | WORKING | T-011 | 2026-11-14 | `python3 scripts/verify/run.py T-011` | New empty Neon project from .env, SSL required, pgvector enabled (D-009). Tables come in T-012 |
| Schema + migrations: mid's 8 tables on Neon | WORKING | T-012 | 2026-11-14 | `python3 scripts/verify/run.py T-012` | Alembic baseline 0001, live schema matches the models, real-app check (sign-up to delete) passes on Neon |
| API scaffold + /health + config | WORKING | T-013 | 2026-11-14 | `python3 scripts/verify/run.py T-013` | Real server answers /health (200, 503 when the DB is down), weak SECRET_KEY refused, API routes need a session |
| Agent session state in PostgreSQL (ADK) | WORKING | T-016 | 2026-11-14 | `python3 scripts/verify/run.py T-016` | DatabaseSessionService on Neon via asyncpg; state survives a restart; hello smoke agent; real Manager + Analysis agents run through it |
| ADK with Groq + OpenRouter (LiteLLM) | WORKING | T-017 | 2026-11-14 | `python3 scripts/verify/run.py T-017` | Live calls through the ADK Runner on both providers; fallback chain skips failing models. Two OpenRouter chain models are gone (Known issues) |
| Environment (DB, API, CI) | IN PROGRESS | T-014..T-019 | | | FastAPI and the schema are built. No Alembic migrations, no CI, ADK session state is in memory not Postgres |
| GitHub PR diff fetch | WORKING | T-030 | 2026-11-14 | `python3 scripts/verify/run.py T-030` | Live: 1-file and 137-file public PRs fetched complete across pages; files without a patch still scored; 404/401 raised |
| Analysis Agent: rule-based risk score | WORKING | T-031 | 2026-11-14 | `python3 scripts/verify/run.py T-031` | End to end on the real server: signed PR webhook -> rule label (equal to the rules alone) + live Groq explanation approved by the Manager; no keys -> same label, 3 attempts, needs human review |
| Module defect history | WORKING | T-032 | 2026-11-14 | `python3 scripts/verify/run.py T-032` | Live: fix commits on the folder (paged, up to 1000) + bug issues; unsafe module names refused (search injection); unknown when lookups fail |
| New-module size-based scoring | WORKING | T-033 | 2026-11-14 | `python3 scripts/verify/run.py T-033` | A module whose files are all new skips history lookups and is scored by size (Low/Medium/High by files + lines); basis and a factor say so |
| Risk questions + majority vote of 3 | WORKING | T-034 | 2026-11-14 | `python3 scripts/verify/run.py T-034` | 4 yes/no questions, strict schema, 3 answers per commit (cached across Manager retries); a yes majority only raises the label (D-011). Live: removed admin check -> High |
| Manager Agent: validation, retry cap, escalation | WORKING | T-035 | 2026-11-14 | `python3 scripts/verify/run.py T-035` | Real Manager loop: pydantic answer schema + content checks, feedback reaches the prompt, cap 3 then human review, unreadable PR not retried. Judgment check deferred to T-039 (D-012) |
| PR and risk dashboard (charts + history) | WORKING | T-036 | 2026-11-14 | `python3 scripts/verify/run.py T-036` | Risk distribution and status donuts, analyses per day (hover + table), issues by type, per-PR history; real API data only; browser-tested with the 33 existing Risk screen tests |
| Dependency graph + live runs and logs | WORKING | T-038 | 2026-11-15 | `python3 scripts/verify/run.py T-038` | Risk Analysis tabs: black-canvas file graph (per-file risk, imports, search, focus, Hide Low) read from GitHub on request; live stage stepper, run log with filters, checks, decision; past runs from the trace log. Not built: minimap, group-by-folder toggle |
| Saved analysis artifacts (D-013) | WORKING | T-094 | 2026-11-15 | `python3 scripts/verify/run.py T-094` | Graph files read from GitHub once per analysed commit (pr_file_snapshots); every run step saved in agent_steps; Risk feed index; agents' in-memory caches capped at 256. Migration 0003 applied on Neon. No Redis/GraphQL (D-013) |
| CI: lint, type check, tests | WORKING | T-019 | 2026-11-15 | `python3 scripts/verify/run.py T-019` | GitHub Actions on every PR and push to main: ruff, mypy (agents, backend), 470 unit tests on SQLite with .env keys blanked, frontend tsc + build. 66 mypy errors fixed. GitHub Actions green from 110a9ad (the first run failed: tests need the built frontend) |
| Risk Analysis dashboard layout | WORKING | T-095 | 2026-11-15 | `python3 scripts/verify/run.py T-095` | View tabs in a sticky pill bar at the top of the Risk page (arrow keys, Home/End); overview as cards: KPIs, Analyse, live runs, charts, PR table. Verixa header, rail and palette unchanged; numbers from the saved feed only. Fixed: donut charts were shrunk to 16px by the global icon rule |
| Pull Requests section, saved authors, tab cache | WORKING | T-096 | 2026-11-15 | `python3 scripts/verify/run.py T-096` | Pull requests view first: every repo PR with its author (pull_requests, migration 0004 on Neon), search, expand, Refresh from GitHub (list re-read only when older than 5 min). Central 3D processing view with the real agent steps while a PR is analysed (comes back after a reload). Views stay mounted and the graph, log, feed and list are cached in the tab: no refetch on switch or reload. Multi-line test names and Tests chips wrap. Card entry transitions. Authors shown as initials (no GitHub images) |
| Webhook receiver + signature check | WORKING | T-022 | 2026-11-14 | `python3 scripts/verify/run.py T-022` | Real server on Neon: signed deliveries accepted, unsigned/wrong/tampered refused 401, bad bodies 400, unconnected repos start no analysis. No body size cap yet (put one at the proxy) |
| D1 Connect GitHub + Jira, webhook | BUILT, UNVERIFIED | T-020..T-022 | 2026-11-02 live | mid: scripts/live_check.py | Signature check verified live. OAuth client credentials missing, so real webhook creation and GitHub/Atlassian sign-in are untested |
| D1 Upload + Test Library | BUILT, UNVERIFIED | T-023..T-025 | 2026-11-02 live | mid: -m scripts.check_database | Strict checks, live preview, create/update/conflict/delete all verified on real PostgreSQL |
| D1 Accounts + 2FA | BUILT, UNVERIFIED | (not in backlog) | 2026-11-02 live | mid: -m scripts.check_database | Email/password sign-in, password rotation, authenticator enrolment with an encrypted secret and 10 hashed recovery codes, cascading delete. GitHub sign-in untested (no OAuth app) |
| LLM router + fallback + model_calls | WORKING | T-026 | 2026-11-14 | `python3 scripts/verify/run.py T-026` | Chains in backend/llm/config.yaml (D-010), live fallback verified, one model_calls row per attempt (tokens, latency, errors masked) |
| D2 Analysis Agent (risk) | BUILT, UNVERIFIED | T-030..T-037 | 2026-11-02 live | mid: scripts/live_check.py | T-030..T-033 built and verified live against real GitHub. T-034 and T-037 not implemented. T-036 still Arisha's |
| Manager Agent (built in wk 5-6) | BUILT, UNVERIFIED | T-035 | 2026-11-02 live | mid: tests/test_analysis_integration.py | Validation, feedback retry, cap at 3, escalation asserted end to end; a live run was accepted on attempt 1 |
| D3 Test selection | NOT STARTED | T-040 | | | |
| D3 Runners (Playwright, Newman) | NOT STARTED | T-041, T-042 | | | Exists in multi-agents/test_agent, still in its testing phase. Not consolidated |
| D3 Failure classification | NOT STARTED | T-043..T-045 | | | As above |
| D3 One-click run (gate 1) | NOT STARTED | T-046 | | | |
| D3 Coverage gap drafting + gate 2 | NOT STARTED | T-047..T-049 | | | |
| D4 Evidence capture + view | NOT STARTED | T-060..T-064 | | | |
| Redaction (built in wk 12-13) | NOT STARTED | T-070 | | | |
| D5 Report Agent | NOT STARTED | T-071, T-072 | | | |
| D5 Jira filing + gate 3 | NOT STARTED | T-073, T-074 | | | |
| Full loop PR -> ticket | NOT STARTED | T-080 | | | |

## Components health
| Component | State | Notes |
|---|---|---|
| PostgreSQL + pgvector | BUILT, UNVERIFIED | Shared Neon database, connected to and exercised live. Holds 3 users, 1 project, and the Test Agent's 8 runs / 195 results / 3 drafts. `risk_assessments` created, additive, empty. Still no Alembic migrations |
| FastAPI backend | BUILT, UNVERIFIED | Boots, serves the API and the built frontend, 401 on protected routes, 401 on an unsigned webhook |
| React dashboard | BUILT, UNVERIFIED | Integrations, Test Library, Security and the new Risk Analysis screen. typecheck and build clean. Not yet driven by Playwright |
| Risk Analysis screen | BUILT, UNVERIFIED | New in `mid/`. Renders real stored agent output; no hardcoded risk values. The API behind it is verified live; the rendering itself has no UI test yet |
| GitHub webhook | BUILT, UNVERIFIED | Signature verified first (wrong signature -> 401 before processing, verified live), 202 immediately, analysis in a background task, repeat deliveries filtered by (project, PR, head sha) |
| Jira connection | BUILT, UNVERIFIED | OAuth and project listing in code. Client credentials missing, so never exercised for real |
| Analysis Agent | BUILT, UNVERIFIED | Rule-based label verified by 24 unit tests and one live run on a real pull request. The model step ran live on Groq and was accepted on attempt 1 |
| Playwright runner | NOT STARTED | |
| Newman runner | NOT STARTED | |
| Groq / OpenRouter / Gemini keys | BUILT, UNVERIFIED | Groq and OpenRouter keys are configured in `mid/.env` and a live Groq call succeeded. Free-tier limits still unchecked (INTEGRATIONS.md). Gemini deliberately unset |
| GitHub / Atlassian OAuth apps | IN PROGRESS | GitHub App set up by Farheen (2026-11-14), not yet verified: T-014 needs a human `run.py T-014 --manual`. Atlassian credentials still placeholders |

## Progress counts
Run /status to compute from BACKLOG.md.
DONE and verified: T-001, T-002, T-010, T-011, T-012, T-013, T-016, T-017, T-022, T-026, T-030, T-031, T-032, T-033, T-034, T-035, T-019, T-036, T-038, T-094, T-095, T-096 (2026-11-14/15, `python3 scripts/verify/run.py T-xxx`). Thirteen are IN REVIEW
(code exists in mid, awaiting /verify and /finish-task); the rest are TODO.

## Known issues
- Done (2026-11-15): the T-010 full re-run after T-036 and T-038 passed.
- Open (T-031, 2026-11-14): reading a public PR with a stored GitHub token returned 401, anonymous reads work. Likely an expired GITHUB_TOKEN in .env or gh login; the app falls back to GITHUB_TOKEN when an account has no linked token. Farheen to check (Claude may not inspect credentials).
- Open (T-031 review): the Manager validates agent output with dict checks, not pydantic models (CLAUDE.md convention), carried over from mid.
- Open (T-030 review, 2026-11-14): GitHub fetch has no retry on 403/429 rate limits and no overall deadline (up to 31 calls of 20 s); a truncated (3000-file) diff is not flagged. Agent I/O for fetch_pr and score_pr is plain dicts, not pydantic (CLAUDE.md convention), carried over from mid. The GitHub client lives in agents/github_client.py, not backend/integrations/.
- Open (found 2026-11-14 in T-017): OpenRouter removed two models in our chains, `qwen/qwen3-8b` (analysis, select,
  classify) and `deepseek/deepseek-v4` (draft). Calls to them fail and the chain moves on to the next model, so Groq
  answers. No OpenRouter replacement is free any more. Farheen will choose replacements later (candidates priced on
  2026-11-14: qwen/qwen3-14b, deepseek/deepseek-v4-flash). Record the choice in DECISIONS.md and config.yaml (T-026).
- Fixed 2026-11-14: `*.log` in .gitignore meant no verification log was ever kept, so every PASS
  row was invalid and the whole backlog was blocked. T-001 re-verified by hand, T-002 re-run (D-006).
- The GitHub and Atlassian OAuth client credentials are missing, so the one-login flow and
  automatic webhook creation cannot be exercised. Everything else in D1 is verified live.
- The existing account's GitHub/Atlassian token and two-step secret were encrypted with the
  original official_ui-main SECRET_KEY and TOTP_ENCRYPTION_KEY, which were never committed. With
  the newly generated keys in `mid/.env` that account must re-link and re-enrol. No data is lost,
  only unreadable. Needs a DECISIONS.md entry.
- No Alembic migrations (T-012). `risk_assessments` references `projects`, so from now on dropping
  the app tables requires dropping the agent table first.
- ADK session state is in memory, so a crash loses an in-flight analysis (T-016).
- `/api/analysis/analyse` runs the agent inline and holds the request open for the length of the
  model chain.

## Open questions
- Final model choice per agent (T-090): a Groq key works; needs the T-037 eval set first
- Which test repo and staging app for the demo (T-018)
- Confirm three human gates with supervisor (T-092)
- T-036: does Arisha's dashboard design replace the Risk Analysis screen built in `mid/`, or build
  on it?
