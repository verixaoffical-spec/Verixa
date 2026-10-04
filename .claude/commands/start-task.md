---
description: Start a task only if all previous work is done and verified
---
Task: $ARGUMENTS

1. Run `python3 .claude/hooks/dependency_gate.py --activate $ARGUMENTS`.
2. If it prints BLOCKED: show the warning exactly as printed, tell the user which person must finish which task first ("first let me complete the previous work"), then STOP. Do not write code, stubs, mocks or workarounds. Offer `/next-task` instead.
3. If it prints CLEAR: set the task to IN PROGRESS in docs/BACKLOG.md, restate the acceptance criteria from docs/TESTING.md for this task, list the files you expect to change, and write a short plan. Wait for the user's go-ahead before coding.
4. Plan the verification script now (scripts/verify/$ARGUMENTS.py, .sh or .spec.ts) and say which tool it will use.
