"""T-038: the changed files of one analysed pull request, with a risk per file and the imports between them,
and the saved steps of its past runs from the trace log. Nothing is stored (P-D8): files are read from GitHub on
request, logs from logs/agent_trace.jsonl.
"""
import json
import os
import posixpath
import re
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import httpx

from agents.github_client import API, _headers, fetch_pr
from agents.risk_rules import is_test_or_doc, module_of, risky_removals, sensitivity
from agents.trace import DEFAULT_FILE

SNAPSHOT_VERSION = 1  # bump when file_risk or imports_of change, so saved snapshots are read again
MAX_FILES = 300        # drawn in the graph; GitHub can list up to 3000
MAX_READ = 40          # files whose content is read to find imports
MAX_BYTES = 200_000    # bigger files are not scanned for imports
CODE = (".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")

JS_IMPORT = re.compile(r"""(?:\bfrom\s+|\bimport\s*\(?\s*|\brequire\s*\(\s*)['"](\.{1,2}/[^'"]+)['"]""")
# shortcut: "import a, b" finds a only, and absolute imports must start at the repo root (no src/ layouts)
PY_IMPORT = re.compile(r"^\s*(?:from\s+(\.*[\w.]*)\s+import\s+\(?([\w*,\s]+?)\)?\s*$|import\s+([\w.]+))", re.M)


def file_risk(f: dict) -> tuple[str, str]:
    """(label, why) for one changed file, from the same rules that score the whole pull request."""
    removed = risky_removals([f])  # before the test check: deleting test cases is itself a risk
    if removed:
        label, reason = removed[0]
        return label, reason.split(f" in {f['filename']}", 1)[0]
    if is_test_or_doc(f["filename"]):
        return "Low", "test or documentation file"
    s = sensitivity([f])
    if s["level"] == "high":
        return "High", "sensitive area: " + s["reasons"][0].split(" (", 1)[-1].rstrip(")")
    if s["level"] == "medium":
        return "Medium", "touches " + s["reasons"][0].split(" (", 1)[-1].rstrip(")")
    return "Low", "no sensitive words in the path or the changed lines"


def _js_targets(path: str, spec: str, paths: set[str]) -> set[str]:
    base = posixpath.normpath(posixpath.join(posixpath.dirname(path), spec))
    stem = base.rsplit(".", 1)[0] if base.endswith((".js", ".mjs", ".cjs")) else base  # TS imports "./x.js" for x.ts
    options = [base] + [stem + e for e in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")] + \
              [base + "/index" + e for e in (".ts", ".tsx", ".js", ".jsx")]
    return {next(o for o in options if o in paths)} if any(o in paths for o in options) else set()


def _py_targets(path: str, text: str, paths: set[str]) -> set[str]:
    by_module = {p[:-3].replace("/", ".").removesuffix(".__init__"): p for p in paths if p.endswith(".py")}
    pkg = posixpath.dirname(path).split("/") if posixpath.dirname(path) else []
    found = set()
    for frm, names, plain in PY_IMPORT.findall(text):
        mod = plain or frm
        if mod.startswith("."):
            dots = len(mod) - len(mod.lstrip("."))
            parent = pkg[:len(pkg) - dots + 1] if dots <= len(pkg) + 1 else []
            mod = ".".join(parent + ([mod.lstrip(".")] if mod.lstrip(".") else []))
        candidates = [mod] + [f"{mod}.{n.strip()}" for n in names.split(",") if n.strip() and n.strip() != "*"]
        found |= {by_module[c] for c in candidates if c in by_module}
    return found


def imports_of(path: str, text: str, paths: set[str]) -> set[str]:
    """Changed files that `path` imports. Relative JS/TS imports and Python module imports only."""
    if path.endswith(".py"):
        out = _py_targets(path, text, paths)
    else:
        out = set().union(*[_js_targets(path, spec, paths) for spec in JS_IMPORT.findall(text)]) if text else set()
    return out - {path}


def _read(repo: str, path: str, sha: str, token: str) -> str:
    try:
        r = httpx.get(f"{API}/repos/{repo}/contents/{quote(path, safe='/')}", params={"ref": sha}, timeout=15,
                      headers={**_headers(token), "Accept": "application/vnd.github.raw+json"})
        return r.text if r.status_code == 200 and len(r.content) <= MAX_BYTES else ""
    except httpx.HTTPError:
        return ""


def pr_files(repo: str, number: int, saved_sha: str, token: str) -> dict:
    """Changed files with a risk each, and the imports between them. Raises httpx.HTTPStatusError if GitHub refuses."""
    pr, files = fetch_pr(repo, number, token)
    head = pr.get("head", {}).get("sha") or ""
    rows = []
    for f in files[:MAX_FILES]:
        label, why = file_risk(f)
        rows.append({"path": f["filename"], "status": f.get("status"), "additions": f.get("additions", 0),
                     "deletions": f.get("deletions", 0), "risk": label, "why": why,
                     "folder": module_of(f["filename"])[1] or "(root)"})
    paths = {r["path"] for r in rows}
    readable = [r["path"] for r in rows if r["path"].endswith(CODE) and r["status"] != "removed"][:MAX_READ]
    with ThreadPoolExecutor(max_workers=8) as pool:
        texts = dict(zip(readable, pool.map(lambda p: _read(repo, p, head, token), readable)))
    edges = sorted([a, b] for a, t in texts.items() for b in imports_of(a, t, paths))
    return {"head_sha": head, "same_commit": head == saved_sha, "total_files": len(files),
            "shown_files": len(rows), "scanned_for_imports": len(readable), "files": rows, "edges": edges}


# ---------- past logs ----------

def _trace_files() -> list[str]:
    path = os.getenv("AGENT_TRACE_FILE", str(DEFAULT_FILE))
    return [p for p in (f"{path}.3", f"{path}.2", f"{path}.1", path) if path and os.path.exists(p)]  # oldest first


def pr_log(repo: str, number: int, describe, limit: int = 2000) -> list[dict]:
    """Every saved run of this pull request, newest first, each with its steps as the live view shows them."""
    pr_id = f"{repo}#{number}"
    lines: deque = deque(maxlen=limit)
    for path in _trace_files():
        with open(path, encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                if pr_id not in raw:
                    continue
                try:
                    line = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(line, dict) and line.get("pr_id") == pr_id:
                    lines.append(line)
    return group_runs([m for m in map(describe, lines) if m])


def group_runs(messages: list[dict]) -> list[dict]:
    """Live-view messages, oldest first, as runs, newest first. Service steps (delivery, saved) carry no run_id, so a
    run is: a delivery or the first step, then everything until the next delivery or a different run_id."""
    runs: list[dict] = []
    for m in messages:
        rid, cur = m.get("run_id"), runs[-1] if runs else None
        if cur is None or m.get("event") == "service.delivery" or (rid and cur["run_id"] and rid != cur["run_id"]):
            cur = {"run_id": rid, "started": m.get("at"), "messages": []}
            runs.append(cur)
        cur["run_id"] = cur["run_id"] or rid
        cur["messages"].append(m)
    return runs[::-1]
