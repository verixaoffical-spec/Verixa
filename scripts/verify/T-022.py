"""T-022 Webhook receiver with signature verification.

Runs the real server (uvicorn subprocess) on the real Neon database and signs deliveries with WEBHOOK_SECRET from
.env (never printed). A temporary account and project are created and deleted again.
Asserts:
  1. A correctly signed ping for a connected repository is accepted (202) and marks the project's webhook verified.
  2. A signed pull_request for a repository nobody connected is accepted (202) and starts no analysis (no row).
  3. A signed pull_request with an action Verixa does not handle (closed) starts no analysis for a connected repo.
Negative cases: no signature, a wrong signature, a valid signature of a different body (tampered), and a non-ASCII
header are refused with 401; a signed body that is not a JSON object gets 400.
"""
import hashlib, hmac, json, os, socket, subprocess, sys, time, uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (".venv/Scripts/python.exe", ".venv/bin/python"):  # run.py uses the system python; the app needs .venv
    _venv = os.path.join(ROOT, _p)
    if os.path.exists(_venv) and os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(_venv):
        sys.exit(subprocess.run([_venv, os.path.abspath(__file__)]).returncode)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


import httpx  # noqa: E402
from sqlalchemy import delete, func, select  # noqa: E402
from backend.agent_db import RiskAssessment  # noqa: E402
from backend.db import Project, SessionLocal, User  # noqa: E402
from backend.settings import settings  # noqa: E402

TAG = uuid.uuid4().hex[:8]
REPO, OTHER = f"verixa-t022/probe-{TAG}", f"verixa-t022/nobody-{TAG}"


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()


def rows_for(repo: str) -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(RiskAssessment).where(RiskAssessment.repo == repo))


def pr_payload(repo: str, action: str) -> bytes:
    return json.dumps({"action": action, "number": 5, "repository": {"full_name": repo},
                       "pull_request": {"number": 5, "title": "probe", "head": {"sha": "c" * 40},
                                        "html_url": f"https://github.com/{repo}/pull/5", "user": {"login": "probe"}}}).encode()


uid, server = None, None
try:
    with SessionLocal() as db:
        user = User(email=f"t022-{TAG}@example.com", name="T-022 probe")
        db.add(user); db.flush()
        db.add(Project(user_id=user.id, repo=REPO, jira_key="T022", jira_name="probe"))
        db.commit()
        uid = user.id
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(port), "--log-level", "warning"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}/webhooks/github"
    for _ in range(90):
        try:
            httpx.get(f"http://127.0.0.1:{port}/health", timeout=5); break
        except httpx.TransportError:
            time.sleep(1)

    def post(body: bytes, event: str, signature: str | None):
        headers = {"x-github-event": event, "x-github-delivery": str(uuid.uuid4()), "content-type": "application/json"}
        if signature is not None:
            headers["x-hub-signature-256"] = signature
        return httpx.post(url, content=body, headers=headers, timeout=20)

    # 1. signed ping for the connected repo
    ping = json.dumps({"zen": "probe", "repository": {"full_name": REPO}}).encode()
    r = post(ping, "ping", sign(ping))
    check("signed ping accepted (202)", r.status_code == 202 and r.json() == {"received": "ping"}, f"{r.status_code} {r.text[:100]}")
    with SessionLocal() as db:
        verified = db.scalar(select(Project.webhook_verified_at).where(Project.repo == REPO))
    check("signed ping marks the project's webhook verified", verified is not None)

    # negatives: signature
    r = post(ping, "ping", None)
    check("negative: no signature -> 401", r.status_code == 401, str(r.status_code))
    r = post(ping, "ping", "sha256=" + "0" * 64)
    check("negative: wrong signature -> 401", r.status_code == 401, str(r.status_code))
    r = post(ping.replace(b"probe", b"evil!"), "ping", sign(ping))
    check("negative: valid signature of a different body (tampered) -> 401", r.status_code == 401, str(r.status_code))
    r = httpx.post(url, content=ping, headers={"x-github-event": "ping", "x-hub-signature-256": "sha256=é".encode("utf-8")}, timeout=20)
    check("negative: non-ASCII signature header -> 401, not a server error", r.status_code == 401, str(r.status_code))

    # negatives: body
    for body, label in ((b"not json", "not JSON"), (b"[1, 2]", "a JSON array")):
        r = post(body, "ping", sign(body))
        check(f"negative: signed body that is {label} -> 400", r.status_code == 400, str(r.status_code))

    # 2./3. pull requests that must not start an analysis
    body = pr_payload(OTHER, "opened")
    r = post(body, "pull_request", sign(body))
    check("signed pull_request for an unconnected repository accepted (202)", r.status_code == 202, str(r.status_code))
    body = pr_payload(REPO, "closed")
    r = post(body, "pull_request", sign(body))
    check("signed pull_request with an unhandled action (closed) accepted (202)", r.status_code == 202, str(r.status_code))
    time.sleep(4)  # the receiver answers first and hands work to a background task
    check("no analysis started for the unconnected repository", rows_for(OTHER) == 0)
    check("no analysis started for the closed pull request", rows_for(REPO) == 0)
finally:
    if server is not None:
        server.terminate()
        try:
            server.wait(timeout=20)
        except subprocess.TimeoutExpired:
            server.kill()
    with SessionLocal() as db:  # remove everything this check made
        db.execute(delete(RiskAssessment).where(RiskAssessment.repo.in_([REPO, OTHER])))
        if uid is not None:
            db.execute(delete(Project).where(Project.user_id == uid))
            db.execute(delete(User).where(User.id == uid))
        db.commit()
    with SessionLocal() as db:
        left = (db.scalar(select(func.count()).select_from(User).where(User.id == uid)) if uid is not None else 0,
                db.scalar(select(func.count()).select_from(Project).where(Project.repo == REPO)),
                rows_for(REPO) + rows_for(OTHER))
    check("cleanup: the temporary account, project and any risk rows are gone", left == (0, 0, 0), str(left))

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
