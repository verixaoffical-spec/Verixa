#!/usr/bin/env python3
"""Dependency gate. Blocks code edits unless the active task's dependencies are DONE and verified.
Modes:
  --hook              PreToolUse hook (reads JSON on stdin). Exit 2 = block.
  --check T-xxx       print gate result for a task
  --activate T-xxx    check, and if clear write .claude/active_task
  --ready [Person]    list TODO tasks that are unblocked
  --clear             remove active task
  --selftest          run built-in tests
"""
import json, os, sys, tempfile, shutil, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as c

EXEMPT_PREFIXES = ("docs/", ".claude/")
EXEMPT_FILES = {"CLAUDE.md", "CLAUDE.local.md", "README.md", "CHANGELOG.md", "CONTRIBUTING.md",
                ".gitignore", ".env.example", ".mcp.json", "CLAUDE.local.md.example"}


def active_task():
    f = c.p(".claude", "active_task")
    if not os.path.exists(f):
        return None
    t = open(f).read().strip().split()
    return t[0] if t else None


def check(tid, rows=None, verif=None, root=None):
    rows = rows if rows is not None else c.load_backlog(root)
    verif = verif if verif is not None else c.load_verification(root)
    if tid not in rows:
        return 2, f"BLOCKED: {tid} is not in docs/BACKLOG.md. Add it to the backlog first."
    if c.num(tid) >= 100:
        left = c.v1_remaining(rows, verif, root)
        if left:
            owners = sorted({rows[t]["lead"] for t in left})
            shown = ", ".join(left[:12]) + (" ..." if len(left) > 12 else "")
            return 2, ("BLOCKED: FYP-2 IS LOCKED. FYP-1 (VERSION 1.0) IS NOT COMPLETE YET.\n"
                       f"{len(left)} FYP-1 tasks are not DONE and verified: {shown}\n"
                       f"Owners still holding work: {', '.join(owners)}. First let us complete the previous work.\n"
                       "Claude must STOP. Do not start any FYP-2 work early. Use /next-task for an unblocked FYP-1 task.")
    bl = c.blockers(tid, rows, verif, root)
    if bl:
        return 2, c.warning(tid, rows, bl)
    return 0, f"CLEAR: {tid} ({rows[tid]['task']}) has all dependencies done and verified."


def hook():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    ti = data.get("tool_input", {}) or {}
    fp = ti.get("file_path") or ti.get("path")
    if not fp:
        return 0
    rel = os.path.relpath(os.path.abspath(fp), c.ROOT).replace("\\", "/")
    if rel.startswith(EXEMPT_PREFIXES) or rel in EXEMPT_FILES:
        return 0
    tid = active_task()
    if not tid:
        print("BLOCKED: no active task. Run /start-task T-xxx first (use /next-task to choose). "
              "Code edits are not allowed without a task whose dependencies are done and verified.", file=sys.stderr)
        return 2
    rows = c.load_backlog()
    if tid in rows and rows[tid]["status"] == "DONE":
        print(f"BLOCKED: {tid} is already DONE. Start a new task with /start-task.", file=sys.stderr)
        return 2
    code, msg = check(tid, rows)
    if code:
        print(msg, file=sys.stderr)
    return code


def ready(person=None):
    rows, verif = c.load_backlog(), c.load_verification()
    for tid, r in rows.items():
        if r["status"] != "TODO":
            continue
        if person and r["lead"] not in (person, "Both"):
            continue
        if not c.blockers(tid, rows, verif):
            print(f"{tid}  {r['lead']:8} {r['task']}")
    return 0


def selftest():
    tmp = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmp, "docs", "verification-logs"))
        open(os.path.join(tmp, "docs", "BACKLOG.md"), "w").write(
            "| T-001 | a | Both | | | DONE |\n| T-002 | b | Farheen | | T-001 | DONE |\n"
            "| T-003 | c | Arisha | | T-002 | TODO |\n| T-004 | d | Arisha | | T-003 | TODO |\n"
            "| T-080 | e | Both | | all above | TODO |\n| T-082 | f | Both | | T-080 | TODO |\n"
            "| T-100 | g | Farheen | | 17-20 | TODO |\n")
        log = "docs/verification-logs/T-001.log"
        open(os.path.join(tmp, log), "w").write("ok")
        sha = hashlib.sha256(b"ok").hexdigest()
        vpath = os.path.join(tmp, "docs", "VERIFICATION.md")
        hdr = "| Task | Date | Method | Command | Result | Log | SHA256 |\n|---|---|---|---|---|---|---|\n"
        open(vpath, "w").write(hdr + f"| T-001 | d | manual | x | PASS | {log} | {sha} |\n")
        rows, verif = c.load_backlog(tmp), c.load_verification(tmp)
        fails = []
        def expect(name, cond):
            print(("ok   " if cond else "FAIL ") + name)
            if not cond: fails.append(name)
        expect("T-002 DONE but unverified blocks T-003", check("T-003", rows, verif, tmp)[0] == 2)
        expect("block message names owner Farheen", "Farheen" in check("T-003", rows, verif, tmp)[1])
        expect("T-004 blocked by TODO T-003", check("T-004", rows, verif, tmp)[0] == 2)
        expect("T-002 clear (T-001 verified)", check("T-002", rows, verif, tmp)[0] == 0)
        open(vpath, "a").write(f"| T-001 | d | auto | x | FAIL | {log} | {sha} |\n")
        verif = c.load_verification(tmp)
        expect("later FAIL cancels earlier PASS", check("T-002", rows, verif, tmp)[0] == 2)
        open(vpath, "a").write(f"| T-001 | d | auto | x | PASS | {log} | {sha} |\n")
        open(os.path.join(tmp, log), "w").write("tampered")
        verif = c.load_verification(tmp)
        expect("tampered log invalidates PASS", check("T-002", rows, verif, tmp)[0] == 2)
        open(os.path.join(tmp, log), "w").write("ok")
        verif = c.load_verification(tmp)
        expect("T-080 'all above' blocked by unfinished tasks", check("T-080", rows, verif, tmp)[0] == 2)
        expect("FYP-II T-100 blocked until T-082", "T-082" in check("T-100", rows, verif, tmp)[1])
        expect("unknown task blocked", check("T-999", rows, verif, tmp)[0] == 2)
        return 1 if fails else 0
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "--hook":
        sys.exit(hook())
    if a[0] == "--check":
        code, msg = check(a[1]); print(msg); sys.exit(code)
    if a[0] == "--activate":
        code, msg = check(a[1]); print(msg)
        if code == 0:
            open(c.p(".claude", "active_task"), "w").write(a[1] + "\n")
            print(f"Active task set to {a[1]}.")
        sys.exit(code)
    if a[0] == "--ready":
        sys.exit(ready(a[1] if len(a) > 1 else None))
    if a[0] == "--clear":
        f = c.p(".claude", "active_task")
        if os.path.exists(f): os.remove(f)
        sys.exit(0)
    if a[0] == "--selftest":
        sys.exit(selftest())
    print(__doc__); sys.exit(1)
