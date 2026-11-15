"""Verification for T-002: Claude Code project setup is intact."""
import json, os, re, subprocess, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, ".claude", "hooks"))
os.environ["CLAUDE_PROJECT_DIR"] = ROOT
import common as c  # noqa: E402  (needs the sys.path line above)

errors = []
def need(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond: errors.append(msg)

for f in ["CLAUDE.md", "README.md", "CONTRIBUTING.md", ".claude/settings.json", ".mcp.json",
          ".claude/hooks/dependency_gate.py", ".claude/hooks/tracking_guard.py", ".claude/hooks/common.py",
          "scripts/verify/run.py", ".claude/hooks/version_status.py", "docs/VERSIONS.md", ".claude/commands/version.md", "docs/BACKLOG.md", "docs/STATUS.md", "docs/VERIFICATION.md",
          "docs/TESTING.md", "docs/CONTRIBUTIONS.md", "docs/DECISIONS.md", "docs/RISKS.md"]:
    need(os.path.exists(os.path.join(ROOT, f)), f"exists: {f}")
for f in os.listdir(os.path.join(ROOT, ".claude", "commands")):
    need(open(os.path.join(ROOT, ".claude", "commands", f)).read().startswith("---"), f"command has frontmatter: {f}")
for f in ["settings.json"]:
    json.load(open(os.path.join(ROOT, ".claude", f)))
json.load(open(os.path.join(ROOT, ".mcp.json")))
for m in re.findall(r"@(docs/[A-Za-z_]+\.md)", open(os.path.join(ROOT, "CLAUDE.md")).read()):
    need(os.path.exists(os.path.join(ROOT, m)), f"CLAUDE.md import resolves: {m}")
rows = c.load_backlog()
need(len(rows) > 50, f"backlog parsed ({len(rows)} tasks)")
missing = [(t, d) for t in rows for d in c.deps_of(t, rows) if d not in rows]
need(not missing, f"all dependencies exist {missing}")
r = subprocess.run([sys.executable, os.path.join(ROOT, ".claude", "hooks", "dependency_gate.py"), "--selftest"],
                   capture_output=True, text=True)
print(r.stdout)
need(r.returncode == 0, "dependency gate selftest passes")
r = subprocess.run([sys.executable, os.path.join(ROOT, ".claude", "hooks", "version_status.py"), "--selftest"],
                   capture_output=True, text=True)
print(r.stdout)
need(r.returncode == 0, "version tracking selftest passes (v1.0 banner, FYP-2 lock)")
need("FYP-1 IS COMPLETED" in open(os.path.join(ROOT, "CLAUDE.md")).read(), "CLAUDE.md contains the v1.0 announcement rule")
sys.exit(1 if errors else 0)
