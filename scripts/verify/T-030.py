"""T-030 GitHub PR diff fetch via integration.

Live, read-only calls to public GitHub pull requests. A token from the GitHub CLI is used when there is one, to
avoid the anonymous rate limit; it is never printed.
Asserts:
  1. A one-file PR (octocat/Hello-World#1) comes back with its title, a 40-character head commit, and every changed
     file with filename, additions, deletions and patch.
  2. A 137-file PR (home-assistant/core#183371) comes back complete across two pages of 100: the number of files
     equals GitHub's changed_files, and no file appears twice.
  3. The Analysis Agent's rule scoring reads the fetched diff (score_pr on the one-file PR returns status ok).
Negative cases: a malformed PR id is refused; a PR that does not exist raises 404; a bad token raises 401.
"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (".venv/Scripts/python.exe", ".venv/bin/python"):  # run.py uses the system python; the app needs .venv
    _venv = os.path.join(ROOT, _p)
    if os.path.exists(_venv) and os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(_venv):
        sys.exit(subprocess.run([_venv, os.path.abspath(__file__)]).returncode)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.update({"AGENT_CI_CHECK": "0", "AGENT_TRACE_CONSOLE": "0"})
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


import httpx  # noqa: E402
from agents.github_client import fetch_pr, parse_pr_id  # noqa: E402

gh = shutil.which("gh")
TOKEN = (subprocess.run([gh, "auth", "token"], capture_output=True, text=True).stdout.strip() or None) if gh else None
SMALL, LARGE = ("octocat/Hello-World", 1), ("home-assistant/core", 183371)

# 1. one-file PR
pr, files = fetch_pr(*SMALL, token=TOKEN)
check("small PR: title and a 40-character head commit", bool(pr.get("title")) and re.fullmatch(r"[0-9a-f]{40}", pr["head"]["sha"] or "") is not None)
check("small PR: file count equals GitHub's changed_files", len(files) == pr["changed_files"] == 1, f"{len(files)} vs {pr.get('changed_files')}")
check("small PR: each file has filename, additions, deletions and patch",
      all({"filename", "additions", "deletions", "patch"} <= set(f) for f in files))

# 2. 137-file PR across two pages
pr, files = fetch_pr(*LARGE, token=TOKEN)
names = [f["filename"] for f in files]
check("large PR: all files fetched across pages (count equals changed_files)", len(files) == pr["changed_files"] and len(files) > 100,
      f"{len(files)} vs {pr.get('changed_files')}")
check("large PR: no file listed twice", len(names) == len(set(names)))

# 3. the Analysis Agent's rules read it
from agents.analysis import score_pr  # noqa: E402
facts = score_pr(f"{SMALL[0]}#{SMALL[1]}", False, TOKEN)
check("score_pr reads the fetched diff and scores it", facts.get("status") == "ok" and facts.get("files_changed") == 1,
      str({k: facts.get(k) for k in ("status", "files_changed", "message")}))

# GitHub leaves out `patch` for binary and very large files: scoring must still work (offline, the fetch faked)
from unittest import mock  # noqa: E402
no_patch = [{"filename": "assets/logo.png", "additions": 0, "deletions": 0, "status": "modified"},
            {"filename": "src/auth/token.ts", "additions": 3, "deletions": 1, "status": "modified", "patch": "+x"}]
info = {"title": "binary", "html_url": "https://github.com/o/r/pull/2", "user": {"login": "d"}, "head": {"sha": "d" * 40},
        "base": {"repo": {"id": 1}}, "changed_files": 2, "additions": 3, "deletions": 1}
with mock.patch("agents.analysis.fetch_pr", return_value=(info, no_patch)), \
     mock.patch("agents.analysis.count_fix_commits", return_value=0), mock.patch("agents.analysis.count_defects", return_value=0):
    facts = score_pr("o/r#2", False, None)
check("a file without a patch (binary or very large) is still scored", facts.get("status") == "ok" and facts.get("files_changed") == 2,
      str({k: facts.get(k) for k in ("status", "files_changed", "message")}))

# negatives
check("parse_pr_id: 'owner/repo#12' -> ('owner/repo', 12)", parse_pr_id("owner/repo#12") == ("owner/repo", 12))
try:
    parse_pr_id("not-a-pr-id")
    refused = False
except ValueError:
    refused = True
check("negative: a malformed PR id is refused", refused)
for label, args, code in (("a PR that does not exist", (SMALL[0], 999999, TOKEN), 404),
                          ("a bad token", (SMALL[0], 1, "ghp_" + "0" * 36), 401)):
    try:
        fetch_pr(*args)
        got = None
    except httpx.HTTPStatusError as exc:
        got = exc.response.status_code
    check(f"negative: {label} raises {code}", got == code, str(got))

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
