#!/usr/bin/env python3
"""Version tracking. Version 1.0 = everything planned for FYP-1, done AND verified.
  --show       progress table for every version (default)
  --brief      one line, for SessionStart
  --announce   print a loud banner for each version newly reached on this machine, then remember it
  --selftest
Per-machine memory of announced versions: .claude/version_seen (gitignored).
"""
import os, sys, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as c

SEEN = c.p(".claude", "version_seen")

V1_BANNER = """
==========================================================================
**FYP-1 IS COMPLETED. VERSION 1.0 IS DONE. NOW FYP-2.**
==========================================================================
 Every FYP-1 task is DONE and VERIFIED. Tag the release: git tag -a v1.0-fyp1
 Next: record it in docs/VERSIONS.md, then start FYP-2 (T-100 onward).
==========================================================================
"""
V2_BANNER = """
==========================================================================
**FYP-2 IS COMPLETED. VERSION 2.0 IS DONE. THE PROJECT IS COMPLETE.**
==========================================================================
 Tag the release: git tag -a v2.0-fyp2. Record it in docs/VERSIONS.md.
==========================================================================
"""


def bar(d, t, w=20):
    f = int(w * d / t) if t else 0
    return "#" * f + "-" * (w - f)


def show(rows=None, verif=None, root=None):
    rows = rows if rows is not None else c.load_backlog(root)
    verif = verif if verif is not None else c.load_verification(root)
    prog, attained = c.progress(rows, verif, root)
    print(f"CURRENT VERSION: {attained}   (v1.0 = FYP-1 complete)")
    for v, name, d, t in prog:
        mark = "DONE " if t and d == t else "     "
        print(f"  {v}  [{bar(d, t)}] {d:>2}/{t:<2} {mark}{name}")
    left = c.v1_remaining(rows, verif, root)
    if left:
        print(f"FYP-1 not finished: {len(left)} tasks left. FYP-2 stays LOCKED.")
    return attained


def announce(rows=None, verif=None, root=None, seen_path=None):
    rows = rows if rows is not None else c.load_backlog(root)
    verif = verif if verif is not None else c.load_verification(root)
    seen_path = seen_path or SEEN
    _, attained = c.progress(rows, verif, root)
    seen = open(seen_path).read().strip() if os.path.exists(seen_path) else "v0.0"
    if seen not in c.ORDER:
        seen = "v0.0"
    new = [v for v in c.ORDER if c.ORDER.index(seen) < c.ORDER.index(v) <= c.ORDER.index(attained)]
    for v in new:
        if v == "v1.0":
            print(V1_BANNER)
        elif v == "v2.0":
            print(V2_BANNER)
        else:
            name = next(m[1] for m in c.MILESTONES if m[0] == v)
            print(f"MILESTONE REACHED: {v} - {name}")
    if new:
        os.makedirs(os.path.dirname(seen_path), exist_ok=True)
        open(seen_path, "w").write(attained + "\n")
    return new


def selftest():
    tmp = tempfile.mkdtemp()
    fails = []
    def expect(n, cond):
        print(("ok   " if cond else "FAIL ") + n)
        if not cond: fails.append(n)
    try:
        # synthetic complete project: every required task DONE+verified
        rows = {f"T-0{i:02d}": {"id": f"T-0{i:02d}", "task": "x", "lead": "Both", "support": "", "dep": "", "status": "DONE"}
                for i in (1, 2, 10, 20, 30, 40, 60, 70, 80, 90)}
        rows["T-093"] = {"id": "T-093", "task": "weekly", "lead": "Both", "support": "", "dep": "", "status": "RECURRING"}
        rows["T-100"] = {"id": "T-100", "task": "mem", "lead": "Farheen", "support": "", "dep": "17-20", "status": "TODO"}
        verif = {t: {"result": "PASS", "log": "l", "sha": "s"} for t in rows}
        real = c.is_verified
        c.is_verified = lambda t, v, root=None: t in v and v[t]["result"] == "PASS"
        sp = os.path.join(tmp, "seen")
        expect("complete FYP-1 attains v1.0", c.progress(rows, verif)[1] == "v1.0")
        expect("recurring task does not block v1.0", "T-093" not in c.v1_remaining(rows, verif))
        out = []
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            announce(rows, verif, seen_path=sp)
        expect("banner says FYP-1 IS COMPLETED", "FYP-1 IS COMPLETED" in buf.getvalue() and "NOW FYP-2" in buf.getvalue())
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            announce(rows, verif, seen_path=sp)
        expect("banner not repeated on same machine", buf2.getvalue().strip() == "")
        rows["T-080"]["status"] = "TODO"
        expect("one unfinished task keeps FYP-1 incomplete", c.progress(rows, verif)[1] != "v1.0")
        expect("gate locks FYP-2 with loud message", "FYP-2 IS LOCKED" in __import__("dependency_gate").check("T-100", rows, verif)[1])
        c.is_verified = real
    finally:
        shutil.rmtree(tmp)
    return 1 if fails else 0


if __name__ == "__main__":
    a = sys.argv[1:] or ["--show"]
    if a[0] == "--show":
        show()
    elif a[0] == "--brief":
        rows, verif = c.load_backlog(), c.load_verification()
        _, att = c.progress(rows, verif)
        left = c.v1_remaining(rows, verif)
        print(f"Verixa version: {att}. " + ("FYP-1 in progress, " + str(len(left)) + " tasks left, FYP-2 locked."
              if left else "FYP-1 COMPLETE. FYP-2 unlocked."))
        announce(rows, verif)
    elif a[0] == "--announce":
        announce()
    elif a[0] == "--selftest":
        sys.exit(selftest())
