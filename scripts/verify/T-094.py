"""T-094 Persist analysis artifacts (D-013).

Asserts:
  1. tests/test_persist.py (unittest, SQLite): a PR's files are read from GitHub once and then served from
     pr_file_snapshots; every live step is written to agent_steps by the background writer and the log route answers
     from the database without reading the trace file; the feed and step indexes exist; the agents' in-memory caches
     forget their oldest entries past the cap. Negatives: a PR that moved past the analysed commit is not saved; a saved
     snapshot is still 404 for another account.
  2. tests/test_pr_views.py (T-038's routes) still pass on top of the cache.
  3. The real database in .env (Neon): Alembic is at head 0003, `alembic check` finds nothing to change, and the two new
     tables and both indexes exist there. Read-only: nothing is written.
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


py = next((os.path.join(ROOT, p) for p in (".venv/Scripts/python.exe", ".venv/bin/python") if os.path.exists(os.path.join(ROOT, p))), sys.executable)

r = subprocess.run([py, "-m", "unittest", "-v", "tests.test_persist", "tests.test_pr_views"], cwd=ROOT, capture_output=True, text=True, timeout=600)
tail = (r.stderr or "").strip().splitlines()
print("     " + " | ".join(tail[-3:]))
check("snapshots, saved steps, indexes, bounded cache, and T-038's routes (unittest)", r.returncode == 0 and tail[-1:] == ["OK"], r.stderr[-800:])

r = subprocess.run([py, "-m", "alembic", "current"], cwd=ROOT, capture_output=True, text=True, timeout=120)
check("Neon: Alembic is at 0003 (head)", "0003 (head)" in r.stdout, (r.stdout + r.stderr)[-300:])
r = subprocess.run([py, "-m", "alembic", "check"], cwd=ROOT, capture_output=True, text=True, timeout=120)
check("Neon: alembic check finds no difference from the models", r.returncode == 0 and "No new upgrade operations" in r.stdout + r.stderr, (r.stdout + r.stderr)[-300:])

probe = ("from sqlalchemy import inspect\nfrom backend.db import engine\ni = inspect(engine)\n"
         "print(engine.dialect.name, sorted(t for t in i.get_table_names() if t in ('pr_file_snapshots','agent_steps')),"
         " 'ix_risk_feed' in {x['name'] for x in i.get_indexes('risk_assessments')},"
         " 'ix_agent_steps_pr' in {x['name'] for x in i.get_indexes('agent_steps')})")
r = subprocess.run([py, "-c", probe], cwd=ROOT, capture_output=True, text=True, timeout=120)
check("Neon: both tables and both indexes exist", r.stdout.strip() == "postgresql ['agent_steps', 'pr_file_snapshots'] True True",
      (r.stdout + r.stderr)[-300:])

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
