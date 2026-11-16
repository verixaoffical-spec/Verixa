"""T-099 Defect history apart from the run's status; branch-based Pull Requests.

Asserts:
  1. tests/test_branches_history.py (unittest, SQLite; GitHub faked at its edges only):
     - GitHub's list and a webhook delivery save each pull request's source and target branch;
     - GET /repo-pulls?branch= (and the sync) keeps only pull requests from or into that branch, still each with its
       own analysis, and always lists every branch with its count;
     - defect_history is "none" for a module with no past defects, "found" with some, "pending" only while the run
       is still going;
     - a new module or a root change logs github.defects_none, which the live view puts in the history stage as info.
     Negatives: an unknown or wildcard branch lists nothing, an overlong one is 422, another account sees no
     branches; a failed lookup is "unknown", never "none"; a module with history is looked up, not reported as none.
  2. The T-096 pull request tests still pass.
  3. Neon (the database in .env), read-only: Alembic is at 0005 (head), `alembic check` finds nothing to change,
     pull_requests has head_ref, base_ref and both branch indexes.
  4. tests/e2e/branches_history.spec.ts (Playwright, real app): the Defect history stage shows "No defect history",
     "2 past defects" (module in its label) or "History unknown" from the saved result, a finished run shows no stage as
     waiting, a run in progress still waits and claims no history; the Pull Requests section shows source → target
     for each pull request, the Branch select lists each branch with its count and filters through the API, search
     and expand still work inside a branch. Negative: a pull request of another branch is not mixed in.
  5. The earlier Risk browser tests still pass, and the frontend builds.
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

r = subprocess.run([py, "-m", "unittest", "-v", "tests.test_branches_history"], cwd=ROOT, capture_output=True, text=True, timeout=600)
tail = (r.stderr or "").strip().splitlines()
print("     " + " | ".join(tail[-3:]))
ran = re.search(r"Ran (\d+) tests", r.stderr or "")
check("backend: branches saved and filtered, defect history apart from the run state (7 tests)",
      r.returncode == 0 and tail[-1:] == ["OK"] and ran is not None and int(ran.group(1)) == 7, r.stderr[-800:])
r = subprocess.run([py, "-m", "unittest", "tests.test_pull_requests"], cwd=ROOT, capture_output=True, text=True, timeout=600)
check("backend: the T-096 pull request tests still pass", r.returncode == 0 and (r.stderr or "").strip().endswith("OK"), r.stderr[-500:])

r = subprocess.run([py, "-m", "alembic", "current"], cwd=ROOT, capture_output=True, text=True, timeout=120)
check("Neon: Alembic is at 0005 (head)", "0005 (head)" in r.stdout, (r.stdout + r.stderr)[-300:])
r = subprocess.run([py, "-m", "alembic", "check"], cwd=ROOT, capture_output=True, text=True, timeout=120)
check("Neon: alembic check finds no difference from the models", r.returncode == 0 and "No new upgrade operations" in r.stdout + r.stderr, (r.stdout + r.stderr)[-300:])
probe = ("from sqlalchemy import inspect\nfrom backend.db import engine\ni = inspect(engine)\n"
         "cols = {c['name'] for c in i.get_columns('pull_requests')}\n"
         "ix = {x['name'] for x in i.get_indexes('pull_requests')}\n"
         "print(engine.dialect.name, {'head_ref', 'base_ref'} <= cols, {'ix_pull_requests_head', 'ix_pull_requests_base'} <= ix)")
r = subprocess.run([py, "-c", probe], cwd=ROOT, capture_output=True, text=True, timeout=120)
check("Neon: pull_requests has head_ref, base_ref and their indexes", r.stdout.strip() == "postgresql True True", (r.stdout + r.stderr)[-300:])

npm, npx = shutil.which("npm"), shutil.which("npx")
r = subprocess.run([npm, "run", "build"], cwd=os.path.join(ROOT, "frontend"), capture_output=True, text=True, timeout=600)
check("frontend type-checks and builds (tsc && vite build)", r.returncode == 0, (r.stdout + r.stderr)[-300:])

# one project at a time: they share the seeded server's data
for project, label in (("branches", "defect history and branch filter in the browser (branches_history.spec.ts)"),
                       ("prs", "Pull Requests section still passes (pull_requests.spec.ts)"),
                       ("refine", "tab indicator and live layout still pass (refinements.spec.ts)"),
                       ("ui", "UI consistency still passes (ui_consistency.spec.ts)"),
                       ("layout", "page layout still passes (risk_layout.spec.ts)"),
                       ("views", "graph and live views still pass (risk_views.spec.ts)"),
                       ("risk", "risk charts still pass (risk_charts.spec.ts)"),
                       ("controlled", "the Risk screen's agent browser tests still pass (agents.spec.ts)")):
    r = subprocess.run([npx, "playwright", "test", f"--project={project}", "--reporter=line"], cwd=E2E,
                       capture_output=True, text=True, timeout=900)
    out = r.stdout + r.stderr
    print("     " + " | ".join(line.strip() for line in out.splitlines() if re.search(r"\d+ (passed|failed|flaky|skipped)", line))[:300])
    check(label, r.returncode == 0 and re.search(r"(\d+) passed", out) is not None and not re.search(r"^\s*\d+ failed", out, re.M), out[-500:])

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
