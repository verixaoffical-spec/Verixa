"""T-019 CI: lint, type check, tests on PR.

Asserts:
  1. .github/workflows/ci.yml runs on pull requests and on pushes to main, and runs ruff, mypy, the unit tests,
     the strict TypeScript check and the frontend build.
  2. Each of those commands passes here, exactly as CI runs it, so CI starts green.
Negative cases: ruff catches an undefined name, mypy catches a wrong argument type, and tsc catches a TypeScript type
error, each planted in a temporary file outside the repo.
"""
import os, shutil, subprocess, sys, tempfile

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


def run(cmd: list[str], cwd: str = ROOT, timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


py = next((os.path.join(ROOT, p) for p in (".venv/Scripts/python.exe", ".venv/bin/python") if os.path.exists(os.path.join(ROOT, p))), sys.executable)
npm = shutil.which("npm") or "npm"
fe = os.path.join(ROOT, "frontend")

# 1. the workflow
wf = yaml.safe_load(open(os.path.join(ROOT, ".github/workflows/ci.yml"), encoding="utf-8"))
on = wf.get("on") or wf.get(True) or {}  # PyYAML reads the bare key `on` as True
check("CI runs on every pull request", "pull_request" in on)
check("CI runs on pushes to main", (on.get("push") or {}).get("branches") == ["main"])
steps = " | ".join(s.get("run", "") for job in wf["jobs"].values() for s in job["steps"])
for cmd in ("ruff check .", "mypy", "python -m unittest discover -s tests -t .", "npm ci", "npm run typecheck", "npm run build"):
    check(f"CI step: {cmd}", cmd in steps)
check("CI installs the pinned dev tools", "pip install -r requirements-dev.txt" in steps)

# 2. the same commands pass here
r = run([py, "-m", "ruff", "check", "."])
check("ruff check . passes", r.returncode == 0, (r.stdout + r.stderr)[-400:])
r = run([py, "-m", "mypy"])
check("mypy (agents, backend) passes", r.returncode == 0 and "Success" in r.stdout, (r.stdout + r.stderr)[-600:])
r = run([npm, "run", "typecheck"], cwd=fe)
check("npm run typecheck passes", r.returncode == 0, (r.stdout + r.stderr)[-400:])
r = run([npm, "run", "build"], cwd=fe)
check("npm run build passes", r.returncode == 0, (r.stdout + r.stderr)[-400:])
r = run([py, "-m", "unittest", "discover", "-s", "tests", "-t", "."], timeout=900)
tail = (r.stderr or "").strip().splitlines()[-3:]
print("     " + " | ".join(tail))
check("unit tests pass", r.returncode == 0 and tail[-1:] == ["OK"], " | ".join(tail))

# negative: each tool really fails on a planted mistake
tmp = tempfile.mkdtemp()
try:
    bad_py = os.path.join(tmp, "bad.py")
    open(bad_py, "w").write("import os\n\ndef add(a: int, b: int) -> int:\n    return a + b\n\nadd('1', 2)\nprint(undefined_name)\n")
    r = run([py, "-m", "ruff", "check", "--no-cache", "--isolated", bad_py])
    check("negative: ruff fails on an undefined name and an unused import",
          r.returncode != 0 and "F821" in r.stdout and "F401" in r.stdout, r.stdout[-300:])
    r = run([py, "-m", "mypy", "--config-file", os.path.join(ROOT, "mypy.ini"), bad_py])
    check("negative: mypy fails on a wrong argument type", r.returncode != 0 and "arg-type" in r.stdout, r.stdout[-300:])
    bad_ts = os.path.join(tmp, "bad.ts")
    open(bad_ts, "w").write("const n: number = 'not a number';\nexport default n;\n")
    tsc = os.path.join(fe, "node_modules", "typescript", "bin", "tsc")
    r = run(["node", tsc, "--noEmit", "--strict", bad_ts])
    check("negative: tsc fails on a type error", r.returncode != 0 and "TS2322" in r.stdout, (r.stdout + r.stderr)[-300:])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
