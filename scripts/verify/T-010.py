"""T-010 Repo init, layout, branch protection.

Asserts:
  1. Every tracked non-.md file of mid (manifest) is in Verixa, byte-identical (SHA256).
  2. None of mid's .md files was imported (Verixa's own README.md is allowed, but must not be mid's copy).
  3. .env is ignored and not tracked; .gitignore keeps mid's patterns; .env.example lists mid's variable names.
  4. The imported test suite passes (unittest, SQLite, never the .env database).
  5. The frontend builds.
  6. main is branch-protected on GitHub.
Negative cases: a tampered copy is caught by the hash check; a planted mid .md is caught;
an unsigned webhook is refused with 401 by the imported app.
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = "verixaoffical-spec/Verixa"
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


def sha(path: str) -> str:
    # CRLF -> LF: git's autocrlf changes line endings per machine, which is not a content change
    return hashlib.sha256(open(path, "rb").read().replace(b"\r\n", b"\n")).hexdigest()


def hash_mismatches(expected: dict[str, str], root: str) -> list[str]:
    return [f for f, h in expected.items() if not os.path.exists(os.path.join(root, f)) or sha(os.path.join(root, f)) != h]


def md_violations(excluded: dict[str, str], root: str) -> list[str]:
    """A mid .md file counts as imported when a byte-identical copy sits at the same path."""
    return [f for f, h in excluded.items() if os.path.exists(os.path.join(root, f)) and sha(os.path.join(root, f)) == h]


def venv_python() -> str | None:
    for p in (".venv/Scripts/python.exe", ".venv/bin/python"):
        if os.path.exists(os.path.join(ROOT, p)):
            return os.path.join(ROOT, p)
    return None


m = json.load(open(os.path.join(ROOT, "scripts/verify/T-010.manifest.json"), encoding="utf-8"))

# 1. byte-identical import
bad = hash_mismatches(m["imported"], ROOT)
check(f"all {len(m['imported'])} mid files imported byte-identical ({m['source']})", not bad, ", ".join(bad[:5]))

# 2. no mid .md files
check(f"none of mid's {len(m['excluded_md'])} .md files imported", not md_violations(m["excluded_md"], ROOT))

# 3. secrets and config
tracked_env = subprocess.run(["git", "ls-files", ".env"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
check(".env is not tracked by git", tracked_env == "")
check(".env is ignored by git", subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT).returncode == 0)
gi = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read().split("\n")
missing = [p for p in m["gitignore_patterns"] if p not in gi]
check(".gitignore keeps all of mid's patterns", not missing, ", ".join(missing))
check("verification logs stay committable", "!docs/verification-logs/*.log" in gi)
example = open(os.path.join(ROOT, ".env.example"), encoding="utf-8").read()
missing = [v for v in m["env_vars"] if f"\n{v}=" not in "\n" + example]
check(".env.example lists mid's variable names", not missing, ", ".join(missing))

# negative: the checks really catch problems
tmp = tempfile.mkdtemp()
try:
    some = next(iter(m["imported"]))
    os.makedirs(os.path.dirname(os.path.join(tmp, some)) or tmp, exist_ok=True)
    shutil.copyfile(os.path.join(ROOT, some), os.path.join(tmp, some))
    check("negative: untouched copy passes the hash check", not hash_mismatches({some: m["imported"][some]}, tmp))
    with open(os.path.join(tmp, some), "ab") as f:
        f.write(b"\n# tampered")
    check("negative: tampered copy is caught by the hash check", hash_mismatches({some: m["imported"][some]}, tmp) == [some])
    md, md_hash = next(iter(m["excluded_md"].items()))
    planted = os.path.join(tmp, "planted")
    os.makedirs(os.path.dirname(os.path.join(planted, md)) or planted, exist_ok=True)
    shutil.copyfile(os.path.join(ROOT, "scripts/verify/T-010.manifest.json"), os.path.join(planted, md))
    check("negative: a different file at a mid .md path is not flagged", not md_violations({md: md_hash}, planted))
    open(os.path.join(planted, md), "wb").write(b"x")
    check("negative: md check flags an identical copy", md_violations({md: sha(os.path.join(planted, md))}, planted) == [md])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# 4. imported test suite, and an unsigned webhook refused by the real app
py = venv_python()
check("virtualenv exists (.venv, from requirements.txt)", py is not None)
if py:
    r = subprocess.run([py, "-m", "unittest", "discover", "-s", "tests", "-t", "."], cwd=ROOT, capture_output=True,
                       text=True, timeout=700)
    tail = (r.stderr or "").strip().splitlines()[-3:]
    print("     " + " | ".join(tail))
    check("imported unit test suite passes", r.returncode == 0 and tail[-1:] == ["OK"], " | ".join(tail))
    probe = ("import tests\nfrom fastapi.testclient import TestClient\nfrom backend.main import app\n"
             "c = TestClient(app)\n"
             "print(c.post('/webhooks/github', content=b'{}', headers={'x-github-event': 'ping'}).status_code)\n"
             "print(c.post('/webhooks/github', content=b'{}', headers={'x-github-event': 'ping',"
             " 'x-hub-signature-256': 'sha256=' + '0' * 64}).status_code)")
    r = subprocess.run([py, "-c", probe], cwd=ROOT, capture_output=True, text=True, timeout=120)
    codes = r.stdout.split()
    check("negative: unsigned webhook refused with 401", codes[:1] == ["401"], r.stderr[-300:])
    check("negative: wrongly signed webhook refused with 401", codes[1:2] == ["401"], r.stderr[-300:])

# 5. frontend builds
npm = shutil.which("npm")
check("npm available", npm is not None)
if npm:
    fe = os.path.join(ROOT, "frontend")
    if not os.path.isdir(os.path.join(fe, "node_modules")):
        subprocess.run([npm, "ci"], cwd=fe, capture_output=True, timeout=600)
    r = subprocess.run([npm, "run", "build"], cwd=fe, capture_output=True, text=True, timeout=600)
    check("frontend builds (npm run build)", r.returncode == 0, (r.stdout + r.stderr)[-300:])

# 6. branch protection
gh = shutil.which("gh")
check("gh available", gh is not None)
if gh:
    r = subprocess.run([gh, "api", f"repos/{REPO}/branches/main", "--jq", ".protected"], capture_output=True, text=True, timeout=60)
    check(f"main is branch-protected on {REPO}", r.stdout.strip() == "true",
          "enable it in GitHub: Settings > Branches (needs the repo owner)")

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
