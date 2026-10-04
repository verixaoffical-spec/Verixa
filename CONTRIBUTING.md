# Contributing

## Branches and commits
- `main` is always working. No direct pushes.
- Branch per task: `feat/T-041-playwright-runner`, `fix/T-044-timeout-bug`, `docs/T-081-demo-script`.
- Commit message: `T-041: add Playwright runner subprocess wrapper`.
- Small PRs. One task per PR where possible.

## Pull requests
- Lead opens the PR, Support reviews. Both approve shared-schema changes.
- PR must: link the task ID, pass lint and tests, update docs/STATUS.md if a feature state changed.
- Use /review in Claude Code before asking for human review.

## Order of work (dependency gate)
- You may only start a task when everything in its Dep column is DONE and verified.
- If you need the other person's unfinished work, do not work around it. Tell them, take a different unblocked task (/next-task), and come back.
- The gate is enforced by a Claude Code hook (`.claude/hooks/`). Do not bypass or edit it. Changes to the gate need both of you and a DECISIONS.md entry.

## Definition of Done
A task is DONE only when:
1. scripts/verify/T-xxx script exists, asserts every acceptance criterion plus a negative case, and `python3 scripts/verify/run.py T-xxx` is PASS
2. Code merged to main
3. Agent tasks: eval set run and result recorded in docs/TESTING.md
4. Docs updated (STATUS, BACKLOG, DATA_MODEL or INTEGRATIONS if touched)
5. No secrets, no hardcoded model names
6. The other person reviewed the PR

## Working with Claude Code
- Flow: /start-session, /next-task, /start-task, build, /verify, /finish-task, /end-session. Skipping steps is how status drifts.
- One task per session where possible. Clear context between unrelated tasks.
- Ask Claude to plan first for anything touching agent logic or shared schema.
- Review Claude's diffs. You are responsible for what you merge.
- If Claude makes a design choice, record it with /decision.

## Versions
v1.0 means FYP-1 is complete (all FYP-1 tasks done and verified). Milestones v0.1 to v0.9 are listed in docs/VERSIONS.md. Tag each release. FYP-2 stays locked until v1.0.

## Weekly rhythm
- Mon: pick tasks for the week in BACKLOG.md.
- Mid-week: 15 min sync, update blockers.
- Fri: update STATUS.md, review risks in docs/RISKS.md, message supervisor if needed.
