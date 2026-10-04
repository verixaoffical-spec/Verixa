---
description: Close a task only after a verified PASS
---
Task: $ARGUMENTS

1. Read the latest row for $ARGUMENTS in docs/VERIFICATION.md. If it is not PASS, or has no row, STOP and tell the user to run /verify $ARGUMENTS first.
2. Run /review (code-reviewer subagent) on the diff. Fix blocking issues, then re-run /verify.
3. Update docs/BACKLOG.md: status DONE. Update docs/STATUS.md feature state to WORKING with today's date and the verify command. Add a CHANGELOG.md entry. Update DATA_MODEL.md, INTEGRATIONS.md or PROMPTS.md if touched.
4. Run `python3 .claude/hooks/dependency_gate.py --clear`.
5. Run `python3 .claude/hooks/version_status.py --announce`. If it prints a banner, say it aloud at the top of your reply in bold capitals (for v1.0: **FYP-1 IS COMPLETED. NOW FYP-2.**), then follow the v1.0 steps in CLAUDE.md. Add the new version to docs/VERSIONS.md.
6. List which tasks this unblocks (`python3 .claude/hooks/dependency_gate.py --ready`) and who owns them, so the other person knows they can start.
