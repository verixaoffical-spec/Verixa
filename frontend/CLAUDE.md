# Frontend rules (React + TypeScript)
- Strict TS. Minimal screens only: connect, test library, PR + risk, run + results, evidence, ticket approval.
- Every consequential action has an explicit button: Run Now, Approve tests, Approve ticket. No auto-submit.
- Data comes from FastAPI REST + WebSocket only. No direct calls to GitHub or Jira.
- Show agent status and retry count so the tester sees what is happening.
- Run: `npm run lint && npm run test && npm run build`
- Work only inside an active task (see root CLAUDE.md). Blocked tasks are not started.
- Verify UI with Playwright: scripts/verify/T-xxx.spec.ts. Use the Playwright MCP to explore, then encode checks as assertions. Record via `python3 scripts/verify/run.py T-xxx`.
