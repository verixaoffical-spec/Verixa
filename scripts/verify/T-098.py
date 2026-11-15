"""T-098 Frontend refinements: frosted glass tab indicator, Live runs and logs without empty space.

Asserts:
  1. tests/e2e/refinements.spec.ts (Playwright, real app on SQLite with the seeded demo data):
     - the Risk view tabs have one indicator that is frosted (backdrop blur), translucent accent purple at every
       stop, and glides (transform transition);
     - after each mouse click and after the End key it covers exactly the selected tab;
     - the selected tab itself has no solid fill;
     - with reduced motion it has no transition;
     - at 1440x900, Live runs and logs puts the log beside its checks at one height and the result beside the tests,
       and the whole view fits one screen, with the decision, checks and tests note all still shown;
     - the run's status dot sits inside its pill.
     Negative: at 820px the live view stacks into one column with no sideways scroll.
  2. The earlier Risk browser tests (UI consistency, Pull Requests, layout, views, charts, agents) still pass, and
     the frontend builds.
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
for project, label in (("refine", "glass tab indicator and Live runs and logs layout (refinements.spec.ts)"),
                       ("ui", "UI consistency still passes (ui_consistency.spec.ts)"),
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
