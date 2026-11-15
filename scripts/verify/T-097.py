"""T-097 UI consistency: landing wording, one shared card surface with depth, Analyses per day section.

Asserts:
  1. tests/e2e/ui_consistency.spec.ts (Playwright, real app on SQLite with the seeded demo data):
     - the dashboard uses the landing page's own terms (read from the landing page in the same run): Pull Requests,
       the Pull request / Risk / Status columns, Agent activity;
     - Risk cards are filled exactly like the landing page's cards (shared/cards.css) and every card has the same
       layered shadow;
     - Analyses per day is a separate full-width section below the small charts;
     - View as table expands it into the full table: every day, totals per day matching the chart and for the week,
       no clipped columns, the chart steps back; the open animation runs; View as chart collapses it again;
     - with reduced motion it opens with no animation.
     Negative: an account with nothing analysed gets no Analyses per day section and no charts.
  2. The earlier Risk browser tests (Pull Requests, layout, views, charts, agents) still pass, and the frontend builds.
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
for project, label in (("ui", "landing wording, shared card surface and depth, Analyses per day section and table (ui_consistency.spec.ts)"),
                       ("prs", "Pull Requests section still passes (pull_requests.spec.ts)"),
                       ("layout", "page layout still passes (risk_layout.spec.ts)"),
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
