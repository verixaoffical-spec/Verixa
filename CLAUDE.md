# Verixa: Agentic AI Quality Engineer

FYP, SZABIST Karachi. Team: Farheen Imam (agent/AI side), Arisha Mumtaz (QA/platform side). Supervisor: Asim Riaz.
Verixa watches a GitHub PR, scores risk, runs relevant tests on staging, gathers evidence, drafts a Jira ticket for human approval.

## DEPENDENCY GATE (highest priority rule)
Work must follow the order in docs/BACKLOG.md. A task may only be started or continued if every task in its Dep column is DONE **and verified** (latest PASS row in docs/VERIFICATION.md).
- Before any coding, run /start-task T-xxx. It runs `.claude/hooks/dependency_gate.py`.
- If the result is BLOCKED: STOP. Show the warning, name the person who owns the unfinished work, and say: "First let me complete the previous work." Do not write code for the blocked task.
- Never stub, mock, fake or "temporarily" implement an unfinished dependency to get around the block.
- Never edit BACKLOG statuses, docs/VERIFICATION.md, verification logs, the hooks or settings to unblock anything.
- This applies equally to Farheen and Arisha. If Arisha's task needs Farheen's unfinished work (or the reverse), the answer is the same: warn, stop, suggest /next-task.
- A hook enforces this on file edits, but the rule also applies to Bash commands that write code. Do not use Bash to get around the hook.
- Only one active task per person. Finish it (/finish-task) before starting another, unless blocked.

## TEST BEFORE FINALIZING (second highest priority)
No feature is finished until a script proves it works.
- Each task gets scripts/verify/T-xxx.(py|sh|spec.ts) that asserts every acceptance criterion in docs/TESTING.md, plus one negative case.
- Use real tools: pytest, httpx/curl for API, psql for DB, Playwright for UI (Playwright MCP for exploring), Newman for Postman collections, eval sets for agents.
- Run only via `python3 scripts/verify/run.py T-xxx` (/verify). It writes the log and the PASS/FAIL row. Do not write those by hand.
- Never claim "done", "working" or "fixed" without a PASS from the runner in this session. Never weaken a test to pass.
- Manual-only checks (for example creating an OAuth App) are run by a human with `--manual`. Claude must not run `--manual`.
- DONE comes only from /finish-task after PASS and a /review.

## VERSION TRACKING (v1.0 = FYP-1)
- **VERSION 1.0 = EVERYTHING PLANNED FOR FYP-1, DONE AND VERIFIED.** Milestones on the way: v0.1 Environment, v0.2 D1 Connect and upload, v0.3 D2 Risk scoring, v0.4 D3 Test run, v0.5 D4 Evidence, v0.6 D5 Report and Jira, v0.9 Integration and demo, then v1.0. FYP-2 is v2.0.
- Always state the current version at session start and in /status. Get it from `python3 .claude/hooks/version_status.py`. Never guess it.
- When /finish-task or the SessionStart hook prints a banner, say it ALOUD at the very top of your reply, exactly in bold capitals:
  **FYP-1 IS COMPLETED. NOW FYP-2.**
  For a smaller milestone say it plainly, for example "MILESTONE REACHED: v0.4".
- Only the script decides when a version is reached. Do not announce v1.0 on your own, and never edit BACKLOG, VERIFICATION or the hooks to reach it.
- On v1.0: tell both Farheen and Arisha, record it in docs/VERSIONS.md, remind them to tag `v1.0-fyp1`, then unlock FYP-2 (T-100 onward).
- Until v1.0, FYP-2 work is blocked by the dependency gate. If asked to start FYP-2 early, refuse and show what FYP-1 work is left.

## Session protocol
1. /start-session: read STATUS, BACKLOG, VERIFICATION, newest dated file in docs/sessions/ (none yet is fine). Ask who is working if CLAUDE.local.md does not say.
2. /next-task <person> then /start-task T-xxx. No unlisted work: add it to the backlog first.
3. Build, then /verify T-xxx, then /finish-task T-xxx.
4. /end-session updates BACKLOG, STATUS, CHANGELOG and writes a session note.
Other commands: /status, /version, /decision, /review, /eval-agent.

## States (be strict)
- Task: TODO > IN PROGRESS > IN REVIEW > DONE. DONE = merged + verified PASS + docs updated.
- Feature in STATUS.md: WORKING only with a PASS row. Built but not run = BUILT, UNVERIFIED. Failing = BROKEN. Say so, do not hide it.

## Docs map (read when relevant)
- @docs/PROJECT.md scope and assumptions
- @docs/ARCHITECTURE.md agents and flow
- @docs/DATA_MODEL.md tables
- @docs/INTEGRATIONS.md GitHub, Jira, Playwright, Newman
- @docs/PERSONAS.md users and dev-side personas
- @docs/CONTRIBUTIONS.md ownership
- @docs/MODELS.md model routing (NOT final)
- @docs/PROMPTS.md prompt registry
- @docs/SECURITY.md secrets and redaction
- @docs/TESTING.md verification protocol, acceptance criteria, evals
- @docs/VERIFICATION.md verification results (machine written)
- @docs/VERSIONS.md version milestones and releases
- @docs/DECISIONS.md decision log
- @docs/GLOSSARY.md terms

## Stack
Google ADK (Python), FastAPI, React + TypeScript, PostgreSQL + pgvector, Playwright (TS specs), Newman, GitHub, Jira.

## Hard product rules
- Three human gates, never bypass: (1) Run Now, (2) approve drafted tests, (3) approve ticket before Jira filing.
- Manager Agent validates every worker output. Retry cap default 3 (D-005), then escalate to human.
- `deployment_pending` is never reported as a failure. Timeouts retry once. Only real bugs reach the Report Agent.
- Strip secrets from logs before any LLM call or ticket attachment.
- Every claim in a ticket cites a log line or artifact.
- Raw evidence on disk, only paths in Postgres.
- Model names live in backend/llm/config.yaml, never hardcoded. Models are undecided.
- Uploaded Playwright specs must be TypeScript.
- FYP-I scope only. FYP-II tasks are blocked until T-082 is verified.
- Never read or print .env. Never commit secrets. Add new vars to .env.example.

## Conventions
- Python: type hints, pydantic for all agent I/O, enums for labels. ruff + mypy.
- TypeScript: strict mode.
- One branch per task: `feat/T-041-playwright-runner`. Commit message starts with the task ID.
- Lead writes the code, the other person reviews the PR. See CONTRIBUTING.md.
- When unsure about ownership, check CONTRIBUTIONS.md and ask.
