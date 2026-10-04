---
description: Review current changes against project rules
---
Run git diff against main. Use the code-reviewer subagent. Check: hard rules in CLAUDE.md, dependency gate respected (no stubs standing in for unfinished dependencies), secrets, hardcoded model names, pydantic schemas on agent I/O, a verification script exists and asserts real behavior, docs updated. Blocking issues first, then suggestions.
