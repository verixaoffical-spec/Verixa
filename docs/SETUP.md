# Setup

## Requirements
Python 3.11+, Node 20+, Docker (for PostgreSQL + pgvector), Git, Claude Code.

## Steps (fill commands in as the repo gets built, task T-010 to T-019)
1. Clone repo, copy `.env.example` to `.env`, fill keys.
2. Copy `CLAUDE.local.md.example` to `CLAUDE.local.md`, fill who you are.
3. Start database: `docker compose up -d db`
4. Backend: create venv, `pip install -r backend/requirements.txt`, run migrations, `uvicorn api.main:app --reload`
5. Frontend: `cd frontend && npm install && npm run dev`
6. Playwright browsers: `npx playwright install`
7. Newman: `npm install -g newman`
8. Verify: `pytest` and `npm run test`
9. Claude Code: open the project, approve the Playwright MCP server when asked (.mcp.json). Confirm hooks load with `/hooks`.
10. Check the gate works: `python3 .claude/hooks/dependency_gate.py --selftest`
11. Windows: if `python3` is not found, replace it with `python` in .claude/settings.json (needs both of you to agree) and in the commands.

## Accounts needed
GitHub (OAuth App + test repo), Atlassian Cloud (Jira project + API token), Groq, OpenRouter, Gemini (free tiers).

## Demo environment
Test repo: TBD. Staging app: TBD (task T-018).
