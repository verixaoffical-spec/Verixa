---
description: Show done, in progress, todo, working and blocked
---
Run `python3 .claude/hooks/version_status.py --show` first and open with the current version. Then read docs/BACKLOG.md, docs/STATUS.md and docs/VERIFICATION.md. Print compactly: counts per status, % done for the current phase, WORKING (verified), BROKEN, BLOCKED (with the unfinished dependency and its owner), and the unblocked TODO tasks per person. Flag any disagreement between BACKLOG, STATUS and VERIFICATION (for example DONE with no PASS).
