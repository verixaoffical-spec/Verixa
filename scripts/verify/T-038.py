"""T-038 PR file graph + per-file risk + past-log endpoints, live stage view (prompt §8 B/C/D, P-D8).

Asserts:
  1. tests/test_pr_views.py (unittest, SQLite): GET /api/analysis/pull-requests/{id}/files gives every changed file a
     risk from the same rules as the PR score, finds the imports between changed files, reports newer commits and
     turns a GitHub refusal into a clear 502; GET .../{id}/log groups the saved trace into runs, newest first, for that
     PR only; every live message carries its stage. Negative: another account's row is 404 on both routes and GitHub
     is never asked; signed out is 401.
  2. tests/e2e/risk_views.spec.ts (Playwright, real app on SQLite): the graph draws each file, its imports, search,
     details and Hide Low; the live view shows a saved run's stages, log, filter, checks and decision from the real
     trace file. Negatives: GitHub refusing the placeholder token shows an error and no graph; a PR with no saved
     steps marks no stage done.
  3. The earlier Risk screen browser tests (risk_charts.spec.ts, agents.spec.ts) still pass, and the frontend builds.
"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
E2E = os.path.join(ROOT, "tests", "e2e")
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


py = next((os.path.join(ROOT, p) for p in (".venv/Scripts/python.exe", ".venv/bin/python") if os.path.exists(os.path.join(ROOT, p))), sys.executable)
r = subprocess.run([py, "-m", "unittest", "-v", "tests.test_pr_views"], cwd=ROOT, capture_output=True, text=True, timeout=600)
tail = (r.stderr or "").strip().splitlines()
print("     " + " | ".join(tail[-3:]))
check("backend: files and log endpoints, stages, ownership (tests/test_pr_views.py)", r.returncode == 0 and tail[-1:] == ["OK"], r.stderr[-800:])

npm, npx = shutil.which("npm"), shutil.which("npx")
r = subprocess.run([npm, "run", "build"], cwd=os.path.join(ROOT, "frontend"), capture_output=True, text=True, timeout=600)
check("frontend type-checks and builds (tsc && vite build)", r.returncode == 0, (r.stdout + r.stderr)[-300:])

for project, label in (("views", "graph and live views (risk_views.spec.ts)"),
                       ("risk", "risk charts still pass (risk_charts.spec.ts)"),
                       ("controlled", "the Risk screen's existing browser tests (agents.spec.ts)")):
    r = subprocess.run([npx, "playwright", "test", f"--project={project}", "--reporter=line"], cwd=E2E,
                       capture_output=True, text=True, timeout=900)
    out = r.stdout + r.stderr
    print("     " + " | ".join(l.strip() for l in out.splitlines() if re.search(r"passed|failed|flaky|skipped", l))[:300])
    check(label, r.returncode == 0 and re.search(r"(\d+) passed", out) is not None and not re.search(r"^\s*\d+ failed", out, re.M), out[-500:])

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
