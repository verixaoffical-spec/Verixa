# Production Plan and Tracker

Plan for taking Verixa from the FYP build to production use. Agreed with Farheen on 2026-11-14.
Status values: TODO | IN PROGRESS | DONE (DONE only with a PASS from `scripts/verify/run.py`).
This file tracks the plan; task status and the gate still live in BACKLOG.md and VERIFICATION.md.

## Decisions
| # | Decision | Status |
|---|---|---|
| P-D1 | Accuracy target is NOT "99% overall". Targets: >=99% critical recall on the planted-bug set, plus reported High precision, abstain rate, and label agreement vs two human labellers | Agreed |
| P-D2 | GitHub App used for check runs and annotations (already set up by Farheen) | Agreed |
| P-D3 | Version columns on `risk_assessments` + Alembic baseline | Waiting: needs explanation, not yet approved |
| P-D4 | Fail policy: rules+scanners decide; model failure never blocks; incomplete = "action required"; crash = failure, retry once, then human | Agreed |
| P-D5 | Import code from `D:\verixa-merging\mid`, leave out all `.md` files | Agreed, blocked by gate (see below) |
| P-D6 | Frontend work uses the ui-ux-pro-max skill | Agreed, plugin to be installed by the user |
| P-D7 | Rules decide the label, the model only explains | Agreed (kept from mid) |
| P-D8 | §8 visuals: components from the 21st catalog (evaluate first, fall back to Recharts + React Flow); per-file data fetched from GitHub on demand (no schema change); past logs read from the trace file (no schema change); charts + logs in T-036, graph + endpoints in new T-038 (Arisha to confirm, she leads both) | Agreed by Farheen 2026-11-14 |
| Open | What is the "Spring" database? What are the "Hacker and Startup AI workflows"? | Waiting for Farheen |

## Blocker found 2026-11-14
`.gitignore` had `*.log`, so no verification log was ever committed. Every PASS row points to a missing
log, so T-001 counts as unverified and the whole backlog is blocked. Fixed in `.gitignore`.
Unblocked 2026-11-14: a human ran `python3 scripts/verify/run.py T-001 --manual --by Both --note "..."` (PASS),
then `run.py T-002` passed. Logs are CRLF on Windows, so `.gitattributes` stores them with `-text`
(otherwise a Mac/Linux checkout changes the bytes and the hash fails).
Every "new task needed" row below must be added to BACKLOG.md before anyone starts it.

## Phases
| Phase | Item | Backlog task | Status |
|---|---|---|---|
| P1 | Import mid code (no .md), keep its layout | T-010 (Arisha lead) | PASS 2026-11-14 (branch protection dropped, D-008) |
| P1 | Copy `.env` (done by the user, Claude never reads it); merge var names into `.env.example` | T-010 | DONE |
| P1 | New database via `DATABASE_URL`, same 8 tables, schema-compare script | T-011, T-012 | TODO, waiting on "Spring" |
| P1 | Run mid's existing tests in the new location | T-010 | DONE: 455 pass |
| P2 | Analysis moved out of the API process into a worker using the DB as queue | new task needed | TODO |
| P2 | Executor sandbox design (no secrets, staging-only egress, gVisor in prod) | new task needed | TODO |
| P2 | Fetch diff by commit (`compare/base...head`) instead of two live calls | new task needed | TODO |
| P2 | Reconciler: re-queue open PRs whose head has no finished row | new task needed | TODO |
| P2 | Base-branch push marks open PRs stale | new task needed | TODO |
| P3 | Context budget + whole enclosing function per hunk | new task needed | TODO |
| P3 | Scanners as evidence: Semgrep, gitleaks, pip-audit / npm audit | new task needed | TODO |
| P3 | Impact graph (ast / tree-sitter, 2 hops, cached per commit), reported as a minimum | new task needed | TODO |
| P3 | Test Library coverage link | new task needed | TODO |
| P3 | Model concern sends row to human review | new task needed | TODO |
| P3 | Claims cite file:line, code checks the line exists | new task needed | TODO |
| P4 | GitHub check run "Verixa risk" on head_sha, annotations, structured report | new task needed | TODO |
| P4 | Executor + test drafting (gate 2) | T-040.. | TODO |
| P4 | Verixa's own CI: ruff, mypy, pytest, eval regression, Playwright | T-019 | TODO |

## Test cases needed
| ID | What it proves | Kind | Status |
|---|---|---|---|
| TC-01 | Imported app starts and mid's existing test suite passes in Verixa | unittest | PASSING (in scripts/verify/T-010.py) |
| TC-02 | No `.md` file from mid was imported; no `.env` is tracked by git | script | PASSING (in scripts/verify/T-010.py) |
| TC-03 | New database has the same tables, columns and foreign keys as mid's | schema compare | TODO |
| TC-04 | Diff is fetched by commit: a push between calls cannot mix two commits | pytest, mocked GitHub | TODO |
| TC-05 | A result for an old commit is marked superseded, never posted as current | pytest | TODO |
| TC-06 | Lost webhook: reconciler re-queues an open PR with no finished row | pytest | TODO |
| TC-07 | Base-branch push marks open PRs stale | pytest | TODO |
| TC-08 | Truncated diff / missing patch / failed history = "incomplete", label >= Medium, human review | pytest | TODO |
| TC-09 | Model down: check still succeeds with the rule label, "explanation unavailable" | pytest | TODO |
| TC-10 | Crash: check = failure, retried once, then human | pytest | TODO |
| TC-11 | Prompt injection in title/diff never changes the label | pytest + eval | TODO |
| TC-12 | Model concern routes the row to human review | pytest | TODO |
| TC-13 | Every claim's file:line exists in the diff, otherwise rejected | pytest | TODO |
| TC-14 | Planted-bug set: removed auth check, added secret, string-built SQL, dropped validation all scored High | eval | TODO |
| TC-15 | Disguised-bug set: same bugs with neutral names / split files still scored High | eval | TODO |
| TC-16 | Safe set: docs/refactor/test PRs, false-positive rate recorded | eval | TODO |
| TC-17 | Held-out set never used for tuning; accuracy drop fails CI | eval in CI | TODO |
| TC-18 | Malicious uploaded spec (child_process via concat, dynamic import, env read) cannot reach secrets | sandbox | TODO |
| TC-19 | Postman request to 169.254.169.254 / DB host is blocked by executor network | sandbox | TODO |
| TC-20 | Test run is tied to the head_sha it ran on | pytest | TODO |
| TC-21 | Check run report has all sections and annotations at the right lines | pytest | TODO |
| TC-22 | Secrets in logs never appear in report or ticket | pytest | TODO |

## Done log
| Date | What | Evidence |
|---|---|---|
| 2026-11-14 | Found and fixed the `*.log` ignore rule that made every verification invalid | `.gitignore` |
| 2026-11-14 | Architecture review of mid and production plan agreed | this file |
| 2026-11-14 | T-002 DONE and verified, committed on feat/T-002-project-setup | VERIFICATION.md |
| 2026-11-14 | prompt.txt §8 (charts, PR node graph, live analysis view) inspected; proposal waiting for approval, no code changed. Belongs to T-036 + a new task after it | https://claude.ai/artifact/7z8gcowPSFuake8vqrwenB |
| 2026-11-14 | §8 design made in-house (no 21st): 4 screens (overview, PR graph, live run + logs, empty/loading/error), example data only. Rules applied: landing-page-design visual system, dataviz checks (risk colours = validated status palette: High #d03b3b, Medium #fab219, Low #0ca30c; legend, hover, table view). Code waits on the gate (T-036 needs T-031) | https://claude.ai/artifact/Uop9Bi19swCD2HqogWeFM8 |
| 2026-11-14 | §8 prototype rebuilt as a real page and checked in a browser at desktop and phone widths: landing page palette and fonts, black-canvas graph (layered left to right, pan, zoom, minimap, search, focus mode), live stepper and console. Risk colours High #d03b3b, Medium #fab219, Low #31c47f. Then checked point by point against prompt §8 and added: severity pie, issues by type, per-commit history (A); PR picker and group-by-folder for large PRs (B, E); files in the run, identified risks, decision (C); run picker for logs (D); titled sections (E) | https://claude.ai/artifact/E8gP5HT7nDBNWZqxfncoxv |
| 2026-11-14 | T-010: 169 mid files imported (no .md), .env copied by Farheen, 455 tests pass, frontend builds. Branch protection dropped by Farheen (D-008); verify PASS | docs/verification-logs/T-010-2026-11-14-171207.log |
