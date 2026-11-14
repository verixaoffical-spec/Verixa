"""T-036 PR and risk dashboard screen (prompt §8 A, design from the approved prototype).

Runs the real app on its own throwaway SQLite database with the seeded demo data (tests/e2e/server.py) and drives
it in Chromium through the real login form.
Asserts:
  1. tests/e2e/risk_charts.spec.ts: the charts show the real counts (risk distribution, analysis status, analyses per
     day with hover details and a table view, issues by type) and the per-commit risk history of a PR; hostile PR
     text never runs. Negative case: an account with no analysed PRs sees no charts, only the empty state.
  2. tests/e2e/agents.spec.ts (the Risk screen's existing browser tests) still pass.
  3. The frontend type-checks and builds.
"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
E2E = os.path.join(ROOT, "tests", "e2e")
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


npx = shutil.which("npx")
npm = shutil.which("npm")
if not os.path.isdir(os.path.join(E2E, "node_modules")):
    subprocess.run([npm, "ci"], cwd=E2E, capture_output=True, timeout=600)

r = subprocess.run([npm, "run", "build"], cwd=os.path.join(ROOT, "frontend"), capture_output=True, text=True, timeout=600)
check("frontend type-checks and builds (tsc && vite build)", r.returncode == 0, (r.stdout + r.stderr)[-300:])

for project, label in (("risk", "risk charts and history (risk_charts.spec.ts)"),
                       ("controlled", "the Risk screen's existing browser tests (agents.spec.ts)")):
    r = subprocess.run([npx, "playwright", "test", f"--project={project}", "--reporter=line"], cwd=E2E,
                       capture_output=True, text=True, timeout=900)
    out = r.stdout + r.stderr
    passed = re.search(r"(\d+) passed", out)
    print("     " + " | ".join(l.strip() for l in out.splitlines() if re.search(r"passed|failed|flaky|skipped", l))[:300])
    check(label, r.returncode == 0 and passed is not None and not re.search(r"^\s*\d+ failed", out, re.M), out[-500:])

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
