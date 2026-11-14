# Changelog
Newest first. Format: date, task ID, what changed, who.

## Unreleased
- 2026-11-14 T-013 Added public GET /health (200 ok, 503 when the database is down, reason logged server-side only); scaffold and config loading verified on a real server (Farheen, via Claude)
- 2026-11-14 T-012 Alembic baseline creates mid's 8 tables on the new Neon database; scripts/check_database.py updated for email-verified sign-up; T-010 check keeps the working-tree hash check with a per-task allowlist (Farheen, via Claude)
- 2026-11-14 T-011 Database moved to a new Neon project (PostgreSQL 18, SSL, pgvector enabled); docker compose kept as local fallback (D-009) (Farheen, via Claude)
- 2026-11-14 T-010 Imported the mid app (169 files, no .md) byte-identical, 455 tests pass, frontend builds. Branch protection dropped from the task (D-008), direct pushes to main for now (D-007), section 8 plan and T-038 recorded (Farheen, via Claude)
- 2026-11-14 T-002 Claude Code project setup verified and closed. Fixed *.log ignore rule that invalidated every verification log, added .gitattributes for byte-exact logs, retry cap set to 3 (D-005), backlog cleanup (D-006), docs/PRODUCTION_PLAN.md added (Farheen, via Claude)
- 2026-09-21 T-001 Proposal submitted (both)
