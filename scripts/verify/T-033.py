"""T-033 New-module size-based scoring.

ARCHITECTURE.md: a module with no history is scored from change size (files + lines), not a fixed default.
Offline: the GitHub fetch and history lookups are faked so each case is an exact pull request.
Asserts:
  1. A PR that only adds a new module is marked as such: scoring_basis says "new module, no history yet" and a
     risk factor explains it.
  2. Its label follows its size: 2 small files -> Low, 5 files / 150 lines -> Medium, 12 files / 800 lines -> High,
     and the score rises with size (not one fixed value).
  3. A change to an existing module uses "size + defect history" and has no new-module factor.
  4. When the history lookups fail on an existing module, the basis says the history is unknown.
Negative case: one modified file inside the module means it is not new.
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (".venv/Scripts/python.exe", ".venv/bin/python"):  # run.py uses the system python; the app needs .venv
    _venv = os.path.join(ROOT, _p)
    if os.path.exists(_venv) and os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(_venv):
        sys.exit(subprocess.run([_venv, os.path.abspath(__file__)]).returncode)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.update({"GITHUB_TOKEN": "", "AGENT_CI_CHECK": "0", "AGENT_TRACE_CONSOLE": "0"})
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


from unittest import mock  # noqa: E402
import httpx  # noqa: E402
from agents.analysis import score_pr  # noqa: E402


def files(n: int, lines: int, status: str = "added", folder: str = "src/reports") -> list[dict]:
    per = max(lines // n, 1)
    return [{"filename": f"{folder}/part{i}.ts", "additions": per, "deletions": 0, "status": status,
             "patch": "+export const value = 1"} for i in range(n)]


_n = iter(range(100, 200))


def score(fs: list[dict], lookups_fail: bool = False) -> dict:
    n = next(_n)  # score_pr caches by PR id and commit, so every case is its own PR
    info = {"title": "t", "html_url": f"https://github.com/o/r/pull/{n}", "user": {"login": "d"}, "head": {"sha": f"{n:040d}"},
            "base": {"repo": {"id": 1}}, "changed_files": len(fs),
            "additions": sum(f["additions"] for f in fs), "deletions": 0}
    fail = {"side_effect": httpx.ConnectError("down")} if lookups_fail else {"return_value": 0}
    with mock.patch("agents.analysis.fetch_pr", return_value=(info, fs)), \
         mock.patch("agents.analysis.count_fix_commits", **fail), mock.patch("agents.analysis.count_defects", **fail):
        return score_pr(f"o/r#{n}", False, None)


small, medium, large = score(files(2, 30)), score(files(5, 150)), score(files(12, 800))
check("new module: scoring_basis says it is scored by size with no history yet",
      "new module, no history yet" in small["scoring_basis"], small["scoring_basis"])
check("new module: a risk factor explains it", any(f.startswith("new module:") for f in small["risk_factors"]))
check("new module: 2 small files -> Low", small["risk_label"] == "Low", small["risk_label"])
check("new module: 5 files, 150 lines -> Medium", medium["risk_label"] == "Medium", medium["risk_label"])
check("new module: 12 files, 800 lines -> High", large["risk_label"] == "High", large["risk_label"])
check("new module: the score rises with size (no fixed default)", small["score"] < medium["score"] < large["score"],
      f"{small['score']} < {medium['score']} < {large['score']}")

existing = score(files(3, 60, status="modified"))
check("existing module: basis is size + defect history", existing["scoring_basis"].startswith("size + defect history"),
      existing["scoring_basis"])
check("existing module: no new-module factor", not any(f.startswith("new module:") for f in existing["risk_factors"]))
unknown = score(files(3, 60, status="modified"), lookups_fail=True)
check("existing module with failed lookups: basis says the history is unknown", "history unknown" in unknown["scoring_basis"],
      unknown["scoring_basis"])

# a new module is not looked up: old bug issues that merely mention the same folder name must not add points
info = {"title": "t", "html_url": "https://github.com/o/r/pull/190", "user": {"login": "d"}, "head": {"sha": f"{190:040d}"},
        "base": {"repo": {"id": 1}}, "changed_files": 2, "additions": 30, "deletions": 0}
with mock.patch("agents.analysis.fetch_pr", return_value=(info, files(2, 30))), \
     mock.patch("agents.analysis.count_fix_commits", return_value=9) as fixes, \
     mock.patch("agents.analysis.count_defects", return_value=9) as issues:
    r = score_pr("o/r#190", False, None)
check("new module: no defect lookups run, so unrelated old bugs add nothing",
      fixes.call_count == 0 and issues.call_count == 0 and r["score"] == small["score"] and r["risk_label"] == "Low",
      f"lookups {fixes.call_count}/{issues.call_count}, score {r['score']} vs {small['score']}")

mixed = files(3, 60)
mixed[1]["status"] = "modified"
m = score(mixed)
check("negative: one modified file in the module means it is not a new module",
      "new module" not in m["scoring_basis"] and not any(f.startswith("new module:") for f in m["risk_factors"]), m["scoring_basis"])

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
