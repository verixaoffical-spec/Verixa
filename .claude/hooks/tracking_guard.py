#!/usr/bin/env python3
"""PostToolUse hook. After BACKLOG.md is edited, block (exit 2) if any DONE task lacks a valid PASS verification."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as c

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
fp = (data.get("tool_input") or {}).get("file_path") or ""
if not fp.replace("\\", "/").endswith("docs/BACKLOG.md"):
    sys.exit(0)
rows, verif = c.load_backlog(), c.load_verification()
bad = [t for t, r in rows.items() if r["status"] == "DONE" and not c.is_verified(t, verif)]
if bad:
    print("TRACKING VIOLATION: marked DONE without a valid PASS in docs/VERIFICATION.md: " + ", ".join(bad) +
          ". Set them back to IN REVIEW, then run /verify <task>. A task is DONE only after its verification script passes.",
          file=sys.stderr)
    sys.exit(2)
sys.exit(0)
