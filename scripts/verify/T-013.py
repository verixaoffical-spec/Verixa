"""T-013 FastAPI scaffold, health route, config loading.

Asserts:
  1. Config loads from .env through backend.settings (required keys present, database URL set), without printing it.
  2. The real server starts (uvicorn in a subprocess) and answers over HTTP:
     GET /health -> 200 {"status": "ok", "database": "ok"} against the real Neon database,
     GET /login  -> 200 HTML (the frontend is served by the same app).
  3. The API routers are mounted and protected: GET /api/analysis/pull-requests without a session -> 401.
Negative cases: a too-short SECRET_KEY is refused at config load; /health answers 503 when the database is unreachable.
"""
import os, socket, subprocess, sys, time

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
from pydantic import ValidationError  # noqa: E402
from backend.settings import Settings, settings  # noqa: E402

# 1. config
check("config loads from .env (secret key, webhook secret, OAuth ids present)",
      len(settings.secret_key) >= 16 and len(settings.webhook_secret) >= 16 and bool(settings.github_client_id))
check("database URL comes from .env, not the localhost default", "localhost" not in settings.database_url)
try:
    Settings(secret_key="short", webhook_secret="x" * 32, github_client_id="a", github_client_secret="b",
             atlassian_client_id="c", atlassian_client_secret="d", _env_file=None)
    refused = False
except ValidationError:
    refused = True
check("negative: a too-short SECRET_KEY is refused", refused)

# 2. the real server over HTTP
with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
server = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app", "--port", str(port), "--log-level", "warning"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
base = f"http://127.0.0.1:{port}"
r = None
try:
    for _ in range(90):
        try:
            r = httpx.get(base + "/health", timeout=10)
            break
        except httpx.TransportError:
            if server.poll() is not None:
                break
            time.sleep(1)
    else:
        r = None
    check("server starts and /health answers 200 ok with the database up",
          r is not None and r.status_code == 200 and r.json() == {"status": "ok", "database": "ok"},
          # server output is not printed: a startup traceback can contain connection details
          (r.text[:200] if r is not None else "no answer") if server.poll() is None else f"server exited with code {server.returncode}")
    up = server.poll() is None
    r = httpx.get(base + "/login", timeout=15) if up else None
    check("/login serves the frontend page", r is not None and r.status_code == 200 and "text/html" in r.headers.get("content-type", ""))
    r = httpx.get(base + "/api/analysis/pull-requests", timeout=15) if up else None
    check("API router mounted and protected: no session -> 401", r is not None and r.status_code == 401,
          f"{r.status_code if r is not None else 'server not running'}")
finally:
    server.terminate()
    try:
        server.wait(timeout=20)
    except subprocess.TimeoutExpired:
        server.kill()

# negative: database unreachable -> 503 (in process, the session factory made to fail)
from unittest import mock  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from backend import main  # noqa: E402

with mock.patch.object(main, "SessionLocal", side_effect=OSError("database down")):
    r = TestClient(main.app).get("/health")
check("negative: /health answers 503 when the database is unreachable",
      r.status_code == 503 and r.json()["database"] == "unreachable", f"{r.status_code} {r.text[:120]}")

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
