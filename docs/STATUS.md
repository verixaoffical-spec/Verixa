# Project Status

Last updated: 2026-10-04 by: Farheen
Version: v0.0 (FYP-1 in progress). **v1.0 = FYP-1 COMPLETE.** Check with /version.
Phase: Pre-build (Claude Code setup). Next: week 3-4 environment.

## State legend
- NOT STARTED
- IN PROGRESS
- BUILT, UNVERIFIED : code exists, not yet run end to end
- WORKING : verified by scripts/verify/run.py with a PASS row in docs/VERIFICATION.md. Record date and command.
- BROKEN : was working or built, now failing. Add note.

## Feature status (FYP-I)
| Feature | State | Tasks | Last verified | Verify with | Notes |
|---|---|---|---|---|---|
| Environment (DB, API, CI) | NOT STARTED | T-010..T-019 | | | |
| D1 Connect GitHub + Jira, webhook | NOT STARTED | T-020..T-022 | | | |
| D1 Upload + Test Library | NOT STARTED | T-023..T-025 | | | |
| LLM router + fallback | NOT STARTED | T-026 | | | |
| D2 Analysis Agent (risk) | NOT STARTED | T-030..T-037 | | | |
| Manager Agent (built in wk 5-6) | NOT STARTED | T-035 | | | |
| D3 Test selection | NOT STARTED | T-040 | | | |
| D3 Runners (Playwright, Newman) | NOT STARTED | T-041, T-042 | | | |
| D3 Failure classification | NOT STARTED | T-043..T-045 | | | |
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
| PostgreSQL + pgvector | NOT STARTED | |
| FastAPI backend | NOT STARTED | |
| React dashboard | NOT STARTED | |
| GitHub webhook | NOT STARTED | |
| Jira connection | NOT STARTED | |
| Playwright runner | NOT STARTED | |
| Newman runner | NOT STARTED | |
| Groq / OpenRouter / Gemini keys | NOT STARTED | check limits |

## Progress counts
Run /status to compute from BACKLOG.md.
DONE: 1 | IN PROGRESS: 1 | TODO: rest

## Known issues
(none)

## Open questions
- Final model choice per agent (T-090)
- Which test repo and staging app for the demo (T-018)
- Confirm three human gates with supervisor (T-092)
- Retry cap value (default 2)
