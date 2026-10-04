---
description: Load project state and plan the session
---
1. Read docs/STATUS.md, docs/BACKLOG.md, docs/VERIFICATION.md and the newest dated file in docs/sessions/ (skip README.md; none yet is fine).
2. Identify who is working (CLAUDE.local.md, else ask).
3. Run `python3 .claude/hooks/version_status.py --announce`; if a banner prints, say it aloud in bold capitals. Open the report with the current version. Report in under 12 lines: what is WORKING (verified), what is BROKEN, blockers, and that person's IN PROGRESS task and unblocked TODO tasks (`python3 .claude/hooks/dependency_gate.py --ready <person>`).
4. Propose one task and wait for confirmation, then use /start-task. Hint: $ARGUMENTS
