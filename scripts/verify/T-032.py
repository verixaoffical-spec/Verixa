"""T-032 Module defect history query.

Live, read-only, anonymous calls to public GitHub repositories (no stored token is used).
Asserts:
  1. count_fix_commits finds bug-fix commits on a busy real folder (python/cpython Lib/asyncio, last 12 months).
  2. count_defects finds bug-labelled issues that mention a real module (microsoft/vscode "terminal").
  3. The fix-commit pattern matches fix/bug/hotfix/regression wording, ignores merge commits and words that only
     contain the letters (prefix, debugging).
  4. More past defects raise the rule score for the same change (the history feeds the risk).
  5. When both lookups fail, scoring still works and says the history is unknown instead of pretending it is zero.
Negative case: a repository that does not exist raises instead of returning 0.
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (".venv/Scripts/python.exe", ".venv/bin/python"):  # run.py uses the system python; the app needs .venv
    _venv = os.path.join(ROOT, _p)
    if os.path.exists(_venv) and os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(_venv):
        sys.exit(subprocess.run([_venv, os.path.abspath(__file__)]).returncode)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.update({"GITHUB_TOKEN": "", "AGENT_CI_CHECK": "0", "AGENT_TRACE_CONSOLE": "0"})  # anonymous reads only
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


import httpx  # noqa: E402
from unittest import mock  # noqa: E402
from agents.github_client import FIX_RE, count_defects, count_fix_commits  # noqa: E402
from agents.risk_rules import assess  # noqa: E402

# 1./2. live lookups
n = count_fix_commits("python/cpython", "Lib/asyncio", 12, None)
check("count_fix_commits finds bug-fix commits on python/cpython Lib/asyncio", n > 0, str(n))
d = count_defects("microsoft/vscode", "terminal", None)
check("count_defects finds bug issues mentioning 'terminal' in microsoft/vscode", d > 0, str(d))

# 3. pattern
yes = ["Fix crash on empty input", "gh-1234: fixes race in loop", "Hotfix for login", "Regression in parser", "bug: wrong total"]
no = ["Add prefix option", "Improve debugging output", "Update docs"]
check("fix pattern matches fix / fixes / hotfix / regression / bug wording", all(FIX_RE.search(m) for m in yes))
check("fix pattern ignores words that only contain the letters (prefix, debugging)", not any(FIX_RE.search(m) for m in no))
merge = [{"commit": {"message": "Merge pull request #9 from x/fix-bug"}}, {"commit": {"message": "Fix the bug\n\nbody"}}]
fake = mock.MagicMock()
fake.__enter__.return_value.get.return_value = mock.MagicMock(json=lambda: merge, raise_for_status=lambda: None)
with mock.patch("agents.github_client.httpx.Client", return_value=fake):
    check("merge commits are not counted as fixes", count_fix_commits("o/r", "src", 12, None) == 1)

# paging: a folder with more than 100 commits is counted past the first page (offline, the client faked)
pages = [[{"commit": {"message": f"Fix issue {i}"}} for i in range(100)], [{"commit": {"message": "Fix one more"}}]]
fake = mock.MagicMock()
fake.__enter__.return_value.get.side_effect = [mock.MagicMock(json=(lambda p=p: p), raise_for_status=lambda: None) for p in pages]
with mock.patch("agents.github_client.httpx.Client", return_value=fake):
    check("fix commits are counted across pages (101 > one page of 100)", count_fix_commits("o/r", "src", 12, None) == 101)

# injection: a folder name that tries to add search qualifiers is refused, not searched
for bad in ('x" repo:other/big "', "a b", ""):
    try:
        count_defects("o/r", bad, None)
        refused = False
    except ValueError:
        refused = True
    check(f"negative: module name {bad!r} is refused before searching", refused)

# 4. history raises the score
files = [{"filename": "src/cart/total.ts", "additions": 20, "deletions": 4, "patch": "+total = sum(items)"}]
s0, s5 = assess(files, 0)["score"], assess(files, 5)["score"]
check("more past defects give a higher score for the same change", s5 > s0, f"{s0} -> {s5}")

# 5. both lookups fail -> unknown, not zero
from agents.analysis import score_pr  # noqa: E402
info = {"title": "t", "html_url": "https://github.com/o/r/pull/3", "user": {"login": "d"}, "head": {"sha": "e" * 40},
        "base": {"repo": {"id": 1}}, "changed_files": 1, "additions": 20, "deletions": 4}
with mock.patch("agents.analysis.fetch_pr", return_value=(info, files)), \
     mock.patch("agents.analysis.count_fix_commits", side_effect=httpx.ConnectError("down")), \
     mock.patch("agents.analysis.count_defects", side_effect=httpx.ConnectError("down")):
    facts = score_pr("o/r#3", False, None)
factors = " ".join(facts.get("risk_factors") or [])
check("when both lookups fail, scoring still works and says the history is unknown",
      facts.get("status") == "ok" and facts.get("past_defects_in_module") is None and "unknown" in factors,
      str({k: facts.get(k) for k in ("status", "past_defects_in_module")}))

# negative
try:
    count_fix_commits("verixa-nobody-xyz/does-not-exist", "src", 12, None)
    got = None
except httpx.HTTPStatusError as exc:
    got = exc.response.status_code
check("negative: a repository that does not exist raises (404), not 0", got == 404, str(got))

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
