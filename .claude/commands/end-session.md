---
description: Update all tracking files before stopping
---
Do in order:
1. Update task statuses in docs/BACKLOG.md. DONE only via /finish-task (needs verified PASS). Unfinished work stays IN PROGRESS or IN REVIEW.
2. Update docs/STATUS.md. WORKING only for things with a PASS row in docs/VERIFICATION.md. Others stay BUILT, UNVERIFIED or BROKEN.
3. Add entries to CHANGELOG.md.
4. Create docs/sessions/YYYY-MM-DD-<name>.md from docs/templates/session.md.
5. Record design choices in docs/DECISIONS.md, new risks or blockers in docs/RISKS.md.
6. Run `python3 .claude/hooks/version_status.py --show` and include the current version in the summary.
7. Show a short summary and list uncommitted work. If a task was left half-done, say plainly who must finish it before dependent tasks can start.
