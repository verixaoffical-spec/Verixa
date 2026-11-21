"""T-089 Premium Risk screens: Overview trend chart and share rings, light theme surfaces, agent scenes, live stages.

Asserts:
  1. tests/e2e/premium.spec.ts (Playwright, real app on SQLite with the seeded demo data):
     - Overview: the Analyses vs flagged risk chart counts the saved analyses for 14 and 30 days, shows both series,
       compares a day on hover and by keyboard; each risk tile's share ring matches the feed's counts;
     - light theme: an expanded pull request is on the page background (#F4F4F8, also under the row hover) and the
       Dependency graph canvas and its nodes are white with dark text; the dark theme keeps both as they were;
     - a live run (signed webhook, PR 106): exactly one agent scene is shown, it moves from the Manager to the Analysis
       agent as the real steps arrive, the agent strip lights the same agent, the scenes cross-fade and each agent's
       scene has its own animation and its own way in; Live runs and logs follows the new pull request by itself,
       its stages arrive one after another, and when it finishes Defect history and CI are grey "not covered" while
       every other stage is green with its time and the track is full.
     Negative: no Test agent scene is shown (the Test agent sends no steps yet); a pull request with no saved steps
     has no green or grey stage and an empty track.
  2. The Live runs layout, graph and live views, and branches and history tests still pass, and the frontend
     type-checks and builds. The other Risk suites run in their own tasks' checks (see below).
"""
import os, re, shutil, subprocess, sys

sys.stdout.reconfigure(encoding="ascii", errors="replace")  # run.py decodes this output with the Windows code page; tool output has ✓ and ›
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
E2E = os.path.join(ROOT, "tests", "e2e")
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


env = dict(os.environ)
env.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")  # the scripted server needs no price list from the network
if not os.path.exists(os.path.join(ROOT, ".env")):
    # A fresh clone has no .env. The e2e server scripts GitHub and the models and never signs in through OAuth,
    # but the settings still require these names, so placeholders are given to it (never real values).
    for name in ("GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET", "ATLASSIAN_CLIENT_ID", "ATLASSIAN_CLIENT_SECRET"):
        env.setdefault(name, "e2e-placeholder")

npm, npx = shutil.which("npm"), shutil.which("npx")
# tsc, then vite into a side folder copied over dist: the running app keeps dist open on Windows, so vite cannot empty it
FE = os.path.join(ROOT, "frontend")
side = os.path.join(FE, "dist-verify")
r = subprocess.run([npx, "tsc"], cwd=FE, capture_output=True, text=True, timeout=600)
if r.returncode == 0:
    r = subprocess.run([npx, "vite", "build", "--outDir", side, "--emptyOutDir"], cwd=FE, capture_output=True, text=True, timeout=600)
if r.returncode == 0:
    shutil.copytree(side, os.path.join(FE, "dist"), dirs_exist_ok=True)
    shutil.rmtree(side, ignore_errors=True)
check("frontend type-checks and builds (tsc && vite build)", r.returncode == 0, (r.stdout + r.stderr)[-300:])

# one project at a time: they share the seeded server's data
for project, label in (("premium", "trend chart, rings, light theme surfaces, agent scenes and live stages (premium.spec.ts)"),
                       ("refine", "glass tab indicator and Live runs and logs layout still pass (refinements.spec.ts)"),
                       ("views", "graph and live views still pass (risk_views.spec.ts)"),
                       ("branches", "defect history and branches still pass (branches_history.spec.ts)")):
    # Trimmed to fit run.py's 900 s on this machine (agreed with the user, 2026-11-21): agents.spec.ts (controlled),
    # ui_consistency, pull_requests, risk_layout and risk_charts are left out here. They keep their own checks
    # (T-095..T-098, agents in T-035/T-096) and all passed on this branch on 2026-11-21 (agents 33/33).
    r = subprocess.run([npx, "playwright", "test", f"--project={project}", "--reporter=line"], cwd=E2E,
                       capture_output=True, text=True, timeout=900, env=env)
    out = r.stdout + r.stderr
    print("     " + " | ".join(line.strip() for line in out.splitlines() if re.search(r"passed|failed|flaky|skipped", line))[:300])
    check(label, r.returncode == 0 and re.search(r"(\d+) passed", out) is not None and not re.search(r"^\s*\d+ failed", out, re.M), out[-500:])

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
