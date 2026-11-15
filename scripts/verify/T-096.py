"""T-096 Pull Requests section, saved authors, live processing view, tab cache, multi-line tests, transitions.

Asserts:
  1. tests/test_pull_requests.py (unittest, SQLite; only GitHub's list is faked):
     - every pull request is saved with its author, state and link, newest activity first;
     - old analyses without an author get it;
     - a fresh list is never read from GitHub again; a forced or stale one is;
     - a webhook delivery saves its pull request and author;
     - removing the project removes its pull requests.
     Negatives: GitHub refusing is a 502 and saves nothing; another account sees none and GitHub is not asked;
     signed out is 401; a POST from another site is 403; javascript: links and foreign avatar hosts are not saved.
  2. tests/test_persist.py and tests/test_pr_views.py (T-094/T-038, which share the routes) still pass.
  3. Neon (the database in .env), read-only: Alembic is at 0004 (head), `alembic check` finds nothing to change,
     pull_requests and ix_pull_requests_feed exist.
  4. tests/e2e/pull_requests.spec.ts (Playwright, real app on SQLite):
     - the Pull Requests view comes first with all 9 pull requests and an Author column, saved in the database;
     - search and expand work, and a reload reads no GitHub list;
     - hidden views read nothing; switching views reads the graph and the log once; a reload shows the graph from
       the cache with no loading message;
     - a pull request being analysed shows the central processing view with real agent steps, and the delivery's
       author;
     - long test text wraps in the Tests chips and the Test Library name cells.
     Negative: an account with no pull requests gets the empty list and no processing view.
  5. The earlier Risk browser tests (layout, views, charts, agents) still pass, and the frontend builds.
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

r = subprocess.run([py, "-m", "unittest", "-v", "tests.test_pull_requests", "tests.test_persist", "tests.test_pr_views"],
                   cwd=ROOT, capture_output=True, text=True, timeout=600)
tail = (r.stderr or "").strip().splitlines()
print("     " + " | ".join(tail[-3:]))
check("backend: pull request list, authors, staleness, webhook save, ownership (+ T-094/T-038 routes)", r.returncode == 0 and tail[-1:] == ["OK"], r.stderr[-800:])

r = subprocess.run([py, "-m", "alembic", "current"], cwd=ROOT, capture_output=True, text=True, timeout=120)
check("Neon: Alembic is at 0004 (head)", "0004 (head)" in r.stdout, (r.stdout + r.stderr)[-300:])
r = subprocess.run([py, "-m", "alembic", "check"], cwd=ROOT, capture_output=True, text=True, timeout=120)
check("Neon: alembic check finds no difference from the models", r.returncode == 0 and "No new upgrade operations" in r.stdout + r.stderr, (r.stdout + r.stderr)[-300:])
probe = ("from sqlalchemy import inspect\nfrom backend.db import engine\ni = inspect(engine)\n"
         "cols = {c['name'] for c in i.get_columns('pull_requests')}\n"
         "print(engine.dialect.name, 'author' in cols and 'listed_at' in cols,"
         " 'ix_pull_requests_feed' in {x['name'] for x in i.get_indexes('pull_requests')})")
r = subprocess.run([py, "-c", probe], cwd=ROOT, capture_output=True, text=True, timeout=120)
check("Neon: pull_requests with its author columns and index exists", r.stdout.strip() == "postgresql True True", (r.stdout + r.stderr)[-300:])

npm, npx = shutil.which("npm"), shutil.which("npx")
r = subprocess.run([npm, "run", "build"], cwd=os.path.join(ROOT, "frontend"), capture_output=True, text=True, timeout=600)
check("frontend type-checks and builds (tsc && vite build)", r.returncode == 0, (r.stdout + r.stderr)[-300:])

# one project at a time: they share the seeded server's data
for project, label in (("prs", "Pull Requests section, cache, processing view, multi-line tests (pull_requests.spec.ts)"),
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
