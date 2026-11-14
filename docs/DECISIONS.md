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
- Context: Farheen is doing Arisha's tasks as well. The repo was made public so GitHub branch rules work on the free plan.
- Decision: until Farheen says otherwise, finished task branches are pushed straight to main without a second reviewer. The /review step (code-reviewer agent) still runs before each finish. The main ruleset blocks deletion and force pushes, and requires a PR once its target branch is set.
- Consequences: no human second review for now; Arisha should read the merged history when she returns. Once the ruleset targets main, work goes back to PRs.
- Owner: Farheen
