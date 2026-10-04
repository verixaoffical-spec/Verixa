#!/usr/bin/env python3
"""Verification runner. The ONLY way a task becomes verified.
  python3 scripts/verify/run.py T-041            runs scripts/verify/T-041.(py|sh|spec.ts), logs, records PASS/FAIL
  python3 scripts/verify/run.py T-014 --manual --by Arisha --note "what you checked"   human only, needs a real terminal
"""
import argparse, datetime, hashlib, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VER = os.path.join(ROOT, "docs", "VERIFICATION.md")
HDR = ("# Verification Log\n\nWritten only by scripts/verify/run.py. Do not edit by hand.\n"
       "Latest row per task counts. A task is verified only if the latest row is PASS and the log hash matches.\n\n"
       "| Task | Date | Method | Command | Result | Log | SHA256 |\n|---|---|---|---|---|---|---|\n")

ap = argparse.ArgumentParser()
ap.add_argument("task")
ap.add_argument("--manual", action="store_true")
ap.add_argument("--by", default="")
ap.add_argument("--note", default="")
a = ap.parse_args()
tid = a.task
stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
logrel = f"docs/verification-logs/{tid}-{stamp}.log"
logabs = os.path.join(ROOT, logrel)
os.makedirs(os.path.dirname(logabs), exist_ok=True)

if a.manual:
    if not sys.stdin.isatty():
        sys.exit("Manual verification must be run by a human in a real terminal, not by Claude.")
    if not a.by or not a.note:
        sys.exit("--by and --note are required for manual verification.")
    out, rc, method, cmd = f"Manual check by {a.by}: {a.note}\n", 0, "manual", f"manual by {a.by}"
else:
    base = os.path.join(ROOT, "scripts", "verify", tid)
    if os.path.exists(base + ".py"):
        argv = [sys.executable, base + ".py"]
    elif os.path.exists(base + ".sh"):
        argv = ["bash", base + ".sh"]
    elif os.path.exists(base + ".spec.ts"):
        argv = ["npx", "playwright", "test", base + ".spec.ts", "--reporter=line"]
    else:
        sys.exit(f"No verification script found for {tid}. Create scripts/verify/{tid}.py, .sh or .spec.ts first.")
    method, cmd = "auto", " ".join(os.path.relpath(x, ROOT) if os.path.isabs(x) else x for x in argv[1:] or argv)
    try:
        r = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=900)
        out, rc = f"$ {' '.join(argv)}\n{r.stdout}\n{r.stderr}\nexit code: {r.returncode}\n", r.returncode
    except subprocess.TimeoutExpired:
        out, rc = "TIMEOUT after 900s\n", 1

open(logabs, "w", encoding="utf-8").write(out)
sha = hashlib.sha256(open(logabs, "rb").read()).hexdigest()
result = "PASS" if rc == 0 else "FAIL"
if not os.path.exists(VER):
    open(VER, "w", encoding="utf-8").write(HDR)
cmd = cmd.replace("|", "/")
open(VER, "a", encoding="utf-8").write(
    f"| {tid} | {datetime.date.today()} | {method} | {cmd} | {result} | {logrel} | {sha} |\n")
print(out)
print(f"{tid}: {result}  (log: {logrel})")
sys.exit(0 if rc == 0 else 1)
