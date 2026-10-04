---
description: Suggest the next unblocked task for a person
---
Person: $ARGUMENTS (Farheen or Arisha).
Run `python3 .claude/hooks/dependency_gate.py --ready $ARGUMENTS`. Pick the earliest by schedule. If the list is empty, run /status and show what each blocked task is waiting on and who owns that work. Explain the pick in 2 lines. Do not start coding until the user confirms and /start-task passes.
