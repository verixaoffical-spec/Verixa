"""Shared helpers for Verixa hooks. Do not edit during normal work (protected in settings.json)."""
import hashlib, os, re

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def p(*parts):
    return os.path.join(ROOT, *parts)


def load_backlog(root=None):
    path = os.path.join(root or ROOT, "docs", "BACKLOG.md")
    rows = {}
    if not os.path.exists(path):
        return rows
    for line in open(path, encoding="utf-8"):
        if re.match(r"\| T-\d+ \|", line):
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) == 6:
                rows[c[0]] = {"id": c[0], "task": c[1], "lead": c[2], "support": c[3],
                              "dep": c[4], "status": c[5]}
    return rows


def load_verification(root=None):
    """Latest row per task. Returns {task: dict}."""
    root = root or ROOT
    path = os.path.join(root, "docs", "VERIFICATION.md")
    latest = {}
    if not os.path.exists(path):
        return latest
    for line in open(path, encoding="utf-8"):
        if re.match(r"\| T-\d+ \|", line):
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) == 7:
                latest[c[0]] = {"task": c[0], "date": c[1], "method": c[2], "command": c[3],
                                "result": c[4], "log": c[5], "sha": c[6]}
    return latest


def is_verified(tid, verif, root=None):
    v = verif.get(tid)
    if not v or v["result"] != "PASS":
        return False
    logp = os.path.join(root or ROOT, v["log"])
    if not os.path.exists(logp):
        return False
    return hashlib.sha256(open(logp, "rb").read()).hexdigest() == v["sha"]


def num(tid):
    return int(tid.split("-")[1])


def deps_of(tid, rows):
    row = rows[tid]
    deps = set(re.findall(r"T-\d+", row["dep"]))
    n = num(tid)
    if "all above" in row["dep"]:
        deps |= {t for t in rows if num(t) < n and num(t) < 100}
    if n >= 100:
        deps |= required_v1(rows)   # no FYP-II work before ALL of FYP-1 (v1.0) is verified
    if tid == "T-140":
        deps |= {t for t in rows if 100 <= num(t) < 140}
    deps.discard(tid)
    return sorted(deps, key=num)


def blockers(tid, rows, verif, root=None):
    out = []
    for d in deps_of(tid, rows):
        r = rows.get(d)
        if r is None:
            out.append((d, "?", "not in BACKLOG.md"))
        elif r["status"] != "DONE":
            out.append((d, r["lead"], f"status is {r['status']}"))
        elif not is_verified(d, verif, root):
            out.append((d, r["lead"], "marked DONE but has no valid PASS in docs/VERIFICATION.md"))
    return out


def warning(tid, rows, bl):
    me = rows[tid]
    lines = [f"BLOCKED: {tid} ({me['task']}) cannot be started or continued.",
             "Previous work it depends on is NOT finished and verified:"]
    owners = []
    for d, lead, why in bl:
        t = rows[d]["task"] if d in rows else ""
        lines.append(f"  - {d} {t} (owner: {lead}): {why}")
        if lead not in owners:
            owners.append(lead)
    for o in owners:
        lines.append(f"Message for {o}: first let me complete the previous work before this one can proceed.")
    lines += ["Claude must STOP this task. Do not stub, mock, skip or work around the missing dependency.",
              "Do not edit BACKLOG.md, VERIFICATION.md or the hooks to unblock. Use /next-task to pick an unblocked task."]
    return "\n".join(lines)


# ---------------- version tracking ----------------
RECURRING = {"T-093"}               # weekly review, never "finished", excluded from v1.0 completion

MILESTONES = [  # (version, name, lo, hi) by task ID range
    ("v0.1", "Environment (DB, API, CI, ADK)", 10, 19),
    ("v0.2", "D1 Connect + upload + LLM router", 20, 29),
    ("v0.3", "D2 Risk scoring + Manager Agent", 30, 39),
    ("v0.4", "D3 Test run + coverage gap drafting", 40, 59),
    ("v0.5", "D4 Evidence collection and view", 60, 69),
    ("v0.6", "D5 Report Agent + Jira filing", 70, 79),
    ("v0.9", "Integration testing + demo", 80, 89),
]
ORDER = ["v0.0"] + [m[0] for m in MILESTONES] + ["v1.0", "v2.0"]


def required_v1(rows):
    return {t for t in rows if num(t) < 100 and t not in RECURRING}


def task_complete(t, rows, verif, root=None):
    return rows[t]["status"] == "DONE" and is_verified(t, verif, root)


def milestone_tasks(version, rows):
    for v, _, lo, hi in MILESTONES:
        if v == version:
            return [t for t in rows if lo <= num(t) <= hi]
    if version == "v1.0":
        return sorted(required_v1(rows), key=num)
    if version == "v2.0":
        return [t for t in rows if num(t) >= 100]
    return []


def progress(rows, verif, root=None):
    """Returns list of (version, name, done, total) and attained version."""
    out = []
    for v, name, lo, hi in MILESTONES:
        ts = milestone_tasks(v, rows)
        out.append((v, name, sum(task_complete(t, rows, verif, root) for t in ts), len(ts)))
    t1 = milestone_tasks("v1.0", rows)
    out.append(("v1.0", "FYP-1 COMPLETE (every FYP-1 task done and verified)",
                sum(task_complete(t, rows, verif, root) for t in t1), len(t1)))
    t2 = milestone_tasks("v2.0", rows)
    out.append(("v2.0", "FYP-2 COMPLETE", sum(task_complete(t, rows, verif, root) for t in t2), len(t2)))
    attained = "v0.0"
    for v, _, d, tot in out:
        if tot and d == tot:
            attained = v
        else:
            break
    # v1.0 / v2.0 depend on everything before them being complete
    if attained in ("v0.9",) and out[-2][2] == out[-2][3]:
        attained = "v1.0"
    if attained == "v1.0" and out[-1][3] and out[-1][2] == out[-1][3]:
        attained = "v2.0"
    return out, attained


def v1_remaining(rows, verif, root=None):
    return [t for t in sorted(required_v1(rows), key=num) if not task_complete(t, rows, verif, root)]
