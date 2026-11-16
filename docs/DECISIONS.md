# Decision Log

## Template
### D-XXX Title (date)
- Context:
- Options:
- Decision:
- Consequences:
- Owner:

### D-001 Config-driven model router, models undecided (2026-10-04)
- Context: free tiers change often, proposal names Gemini + Groq, priority table prefers Groq/OpenRouter.
- Options: hardcode one model; config-driven router with eval-based ordering.
- Decision: router with config.yaml, final order decided after evals.
- Consequences: need eval sets early, need ADK non-Gemini wrapper (T-017).
- Owner: Farheen

### D-002 Three human gates instead of two (2026-10-04)
- Context: proposal text names run and filing gates, proposal diagram also shows test-case approval.
- Decision: implement three gates. Confirm with supervisor.
- Consequences: approvals table has gate column; extra UI step after drafting.
- Owner: Both

### D-003 Dependency gate and mandatory verification (2026-10-04)
- Context: with two people and Claude Code, status drifts and work gets built on unfinished parts.
- Decision: a hook blocks code edits unless the active task's dependencies are DONE and verified. DONE needs a PASS written by scripts/verify/run.py. Hooks, runner and verification files are protected from Claude edits.
- Consequences: slower starts, fewer integration surprises. Bash-based writes are not blocked by the hook, so the rule in CLAUDE.md and code review cover that gap.
- Owner: Both

### D-004 Version tracking, v1.0 = FYP-1 complete (2026-10-04)
- Context: we need an unambiguous point where FYP-1 is finished and FYP-2 may start.
- Decision: v1.0 is reached only when every FYP-1 task (except recurring T-093) is DONE and verified. FYP-2 tasks are locked by the gate until then. Claude announces it in bold capitals: FYP-1 IS COMPLETED. NOW FYP-2.
- Consequences: FYP-2 cannot start early even if FYP-1 has leftover small tasks. Close or re-scope them before the demo.
- Owner: Both

### D-005 Manager retry cap is 3 (2026-11-14)
- Context: CLAUDE.md said default 2, the built Manager in mid uses MAX_ATTEMPTS = 3.
- Decision: keep 3 attempts, then escalate to human review. CLAUDE.md updated to match.
- Consequences: one extra model call in the worst case before escalation.
- Owner: Farheen

### D-006 Backlog cleanup and work order after the mid consolidation (2026-11-14)
- Context: T-011, T-012, T-016 and T-026 were IN PROGRESS from the mid consolidation while T-002 was also open, breaking "one active task per person". Their code is partial (see BACKLOG consolidation notes).
- Decision: set them back to TODO; the partial code in mid is reused when each task is started in order. Farheen instructed Claude to work through FYP-1 tasks in numbering order for both people, including Arisha-led tasks (starting with T-010, importing mid without .md files). Ownership in CONTRIBUTIONS.md is unchanged; the owner reviews the work.
- Consequences: Arisha must review the Arisha-led tasks Claude completes (superseded for now by D-007). Root cause found: `*.log` in .gitignore meant no verification log was ever kept, so every PASS was invalid; fixed with a .gitignore exception and .gitattributes `-text`.
- Owner: Farheen

### D-007 Farheen covers both roles; direct pushes to main for now (2026-11-14)
- Context: Farheen is doing Arisha's tasks as well. The repo is now public.
- Decision: until Farheen says otherwise, finished task branches are pushed straight to main without a second reviewer. The /review step (code-reviewer agent) still runs before each finish.
- Consequences: no human second review for now; Arisha should read the merged history when she returns. Branch protection: see D-008.
- Owner: Farheen

### D-008 Branch protection removed from T-010 (2026-11-14)
- Context: T-010 asked for branch protection on main. While the repo was private GitHub would not enforce it on the free plan. After making it public, three rulesets were created but none took effect ("main" active with no target branch, "main1" and "main2" disabled). The pushing account (farheenimam) has write access, not admin, so a required-PR rule with an admin bypass would block the direct pushes agreed in D-007. Setting this up was slowing the work down.
- Decision: Farheen removed branch protection from T-010's acceptance criteria. scripts/verify/T-010.py no longer checks it. This is a change of requirement by the owner, not a test weakened to pass. Arisha (T-010 lead) should sign off when she returns.
- Consequences: as of today nothing protects main, so anyone with write access can delete or force-push it. Optional safety net later: activate the "main1" ruleset (blocks deletion and force pushes, does not require PRs).
- Owner: Farheen

### D-009 Neon PostgreSQL instead of docker compose for T-011 (2026-11-14)
- Context: Docker is not installed on Farheen's machine. Farheen created a new, empty Neon project and put its connection string in .env (DATABASE_URL).
- Decision: T-011 uses that Neon database (PostgreSQL 18, SSL required, pgvector enabled). docker-compose.yml stays as an optional local fallback. Tests keep using SQLite by default (tests/__init__.py), never the .env database.
- Consequences: the shared database is in the cloud, so anything a check writes must clean up after itself. The older Neon database used by mid is no longer the app's database.
- Owner: Farheen

### D-010 The LLM router stays in agents/llm.py; config at backend/llm/config.yaml (2026-11-14)
- Context: ARCHITECTURE.md and backend/CLAUDE.md plan backend/llm/router.py. The working router came from mid as agents/llm.py (chains, fallback, ask()), and the agents package does not import the backend.
- Decision: keep the router in agents/llm.py and move only the model names into backend/llm/config.yaml (T-026). model_calls rows are written by backend/model_calls.py from the agents' trace, so the agents still never touch the database.
- Consequences: "llm/router.py" in the docs means agents/llm.py. Changing models means editing config.yaml (or <TASK>_MODELS in .env), never code.
- Owner: Farheen

### D-011 Risk questions can only raise the rule label (2026-11-14)
- Context: PROMPTS.md plans yes/no risk questions that "feed the rule score", and MODELS.md a majority vote of 3. P-D7 says the rules decide the label and the model only explains, and a model answer that could lower a label would let text in a PR talk its own risk down.
- Decision: T-034 asks 4 yes/no questions (auth, money, validation, data), 3 times on the first working model at temperature 0.7, answers checked against a strict pydantic schema. A question with at least 2 of 3 yes (all 3 answers usable) raises the label to that question's minimum (auth/money High, validation/data Medium). "No" never lowers. A 2-1 split is shown as low confidence. Every vote is listed in risk_factors. RISK_QUESTIONS=0 turns it off.
- Consequences: about 3 extra small model calls per PR, run at the same time. Disguised risky changes the keyword rules miss can still reach High (TC-15). When the chains have 3 working models, the vote can move to one answer per model.
- Owner: Farheen

### D-012 Manager judgment check deferred to its own task, T-039 (2026-11-14)
- Context: MODELS.md and TESTING.md describe a Manager "judgment check": a model asked twice whether a claim is supported by evidence, disagreement routed to a human. It is not built, and T-035's title covers validation, retry cap and escalation only. Its real use is the Report Agent's root-cause claims (D5), which do not exist yet.
- Decision: T-035 closes on validation (now with a pydantic answer schema), the retry cap of 3 and escalation. The judgment check becomes T-039, after T-035, to be built when the Report Agent gives it claims to judge.
- Consequences: until T-039, no second-opinion check runs; every Analysis answer still passes the plain-code validation. The TESTING.md safety check "disagreement routes to human" is open until then.
- Owner: Farheen

### D-013 Save analysis artifacts in Postgres; no Redis or GraphQL for now (2026-11-15)
- Context: the Dependency graph called GitHub up to ~71 times on every open, run logs lived only in a log file that rotates at 5 MB, the agents' in-memory caches grew without limit, and the Risk feed had no index matching its query. Farheen asked for data to be saved so a refresh never redoes work, and asked about Redis and GraphQL.
- Options: Redis cache; GraphQL API; Postgres tables + indexes.
- Decision: T-094 adds pr_file_snapshots (one per analysed commit, immutable, served from the database after the first read) and agent_steps (every run step, indexed by repo, PR and time), a composite index on risk_assessments, and a size cap on the agents' in-memory caches. No Redis (one app server, no Docker, memory is tight; Postgres rows survive restarts) and no GraphQL (the REST routes already return one screen's data each). Approved by Farheen.
- Consequences: a shared schema change through Alembic migration 0003; Arisha must be told. Redis can come back if the app runs on more than one server.
  - The first graph read decides: a PR still on its analysed commit is saved and always shown at that commit; one that had already moved on is shown at its newer commit and read again each time. Snapshots carry a rules version (SNAPSHOT_VERSION) and are read again when the rules change.
  - Once a PR has steps in agent_steps, its log shows only those; runs from before T-094 stay in the rotating trace file. Reading both would re-read the file on every open.
  - agent_steps has no retention and no link to a project, so steps stay after a project is deleted. Fine at FYP size; add cleanup if it grows.
- Owner: Farheen

### D-014 Pull requests saved in Postgres; Risk screens cached in the browser tab (2026-11-15)
- Context: Farheen's prompt asked for a Pull Requests section listing every pull request of the repository with its author saved in Neon, and for logs and the dependency graph to show at once on tab switches and reloads.
- Decision: T-096 adds the pull_requests table (migration 0004, a shared schema change: Arisha must be told), filled from GitHub's list when the saved one is older than 5 minutes and from each webhook delivery. In the browser, every Risk view stays mounted, and what it read is kept in memory and in the tab's sessionStorage, cleared on sign out and on a lost session. Authors are shown as initials: the page loads no images from GitHub (frontend/CLAUDE.md, CSP img-src 'self').
- Consequences:
  - The graph is cached per analysis. A PR that had moved past its analysed commit (D-013 reads it live each time) is now kept as first read until the tab closes or the user signs out; a new analysis is a new key.
  - The browser cache is per tab, not per account: signing in as someone else in another tab leaves this tab's lists until its next 401 or reload.
  - rows_json reads all of a project's analyses to find the latest per PR; fine at FYP size, a DISTINCT ON query later.
- Owner: Farheen

### D-015 Defect history apart from run status; branch filter matches source or target (2026-11-16)
- Context: Farheen's prompt: new pull requests showed "Waiting" under Defect history, and Pull Requests should be viewable by branch with source and target saved in Neon.
- Decision: T-099. When a change has nothing to look up (a new module or a root change), the Analysis agent logs github.defects_none, so the history stage reports. The result is a separate field (defect_history: none, found, unknown, pending), shown as a chip under the stage; "waiting" is shown only while a run is going. A failed lookup stays "unknown", never "none". pull_requests gets head_ref and base_ref (migration 0005, a shared schema change: Arisha must be told). A branch filter matches a pull request coming from or going into the branch, compared exactly. Analyses, logs and graphs stay keyed by pull request, so a branch view never mixes them.
- Consequences: rows saved before 0005 have no branch until the next list read (within 5 minutes of opening Pull Requests) or delivery, and appear only under All branches until then. The branch list is computed from the saved rows on each read; fine at FYP size.
- Owner: Farheen
