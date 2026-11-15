"""T-095 Risk Analysis dashboard layout (prompt.txt).

Asserts:
  1. tests/e2e/risk_layout.spec.ts (Playwright, real app on SQLite with the seeded demo data):
     - the view tabs are a pill bar at the very top of the Risk page, above the title, and stay there while scrolling;
     - the overview is cards in order (KPIs, Analyse, charts, pull request table);
     - every KPI and row count equals the saved feed from /api/analysis/pull-requests;
     - opening the page and switching views sends no analysis request;
     - Verixa's own main navigation is unchanged;
     - the donut charts render at full size;
     - at phone width nothing scrolls sideways.
     Negative: an account with nothing analysed gets the tabs and an empty table card, no charts or rows.
  2. The earlier Risk screen browser tests (risk_views, risk_charts, agents.spec.ts) still pass on the new layout,
     and the frontend type-checks and builds.
"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
E2E = os.path.join(ROOT, "tests", "e2e")
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


npm, npx = shutil.which("npm"), shutil.which("npx")
r = subprocess.run([npm, "run", "build"], cwd=os.path.join(ROOT, "frontend"), capture_output=True, text=True, timeout=600)
check("frontend type-checks and builds (tsc && vite build)", r.returncode == 0, (r.stdout + r.stderr)[-300:])

# one project at a time: they share the seeded server's data
for project, label in (("layout", "tabs on top, card layout, saved-feed numbers, phone width, empty account (risk_layout.spec.ts)"),
                       ("views", "graph and live views still pass (risk_views.spec.ts)"),
                       ("risk", "risk charts still pass (risk_charts.spec.ts)"),
                       ("controlled", "the Risk screen's agent browser tests still pass (agents.spec.ts)")):
    r = subprocess.run([npx, "playwright", "test", f"--project={project}", "--reporter=line"], cwd=E2E,
                       capture_output=True, text=True, timeout=900)
    out = r.stdout + r.stderr
    print("     " + " | ".join(line.strip() for line in out.splitlines() if re.search(r"passed|failed|flaky|skipped", line))[:300])
    check(label, r.returncode == 0 and re.search(r"(\d+) passed", out) is not None and not re.search(r"^\s*\d+ failed", out, re.M), out[-500:])

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
