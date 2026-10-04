---
description: Test the task with a real script and record the result
---
Task: $ARGUMENTS

1. Make sure scripts/verify/$ARGUMENTS.(py|sh|spec.ts) exists. If not, write it with the test-writer or verifier subagent. It must assert results, cover every acceptance criterion in docs/TESTING.md, and include a negative case. Use the right tool: pytest, httpx/curl, psql, Playwright (Playwright MCP may be used to explore the UI first), Newman.
2. Start whatever it needs (database, backend, staging app).
3. Run `python3 scripts/verify/run.py $ARGUMENTS`. This is the only valid way to record a result.
4. PASS: report it and suggest /finish-task. FAIL: show the failing assertion, fix the code, re-run. Never edit the verification log, VERIFICATION.md, the runner or the hooks. Never weaken a test to make it pass.
5. Manual-only tasks (for example registering an OAuth App): ask the human to run `python3 scripts/verify/run.py <task> --manual --by <name> --note "<what was checked>"` in their own terminal. Claude must not run --manual.
