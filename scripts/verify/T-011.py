"""T-011 PostgreSQL + pgvector, on Neon (D-009).

Asserts:
  1. DATABASE_URL (read by the app's settings from .env, never printed) is a Neon PostgreSQL host with SSL required.
  2. The server is PostgreSQL 15 or newer and the app's own engine (backend.db.engine) connects to it.
  3. pgvector can be enabled, and vector distance works (in a temporary table that disappears with the session).
  4. .env is not tracked by git; docker-compose.yml still offers the local pgvector fallback.
Negative case: the same host with a wrong password is refused.
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# run.py starts this with the system python; the app's packages live in .venv, so re-run there
for _p in (".venv/Scripts/python.exe", ".venv/bin/python"):
    _venv = os.path.join(ROOT, _p)
    if os.path.exists(_venv) and os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(_venv):
        sys.exit(subprocess.run([_venv, os.path.abspath(__file__)]).returncode)
sys.path.insert(0, ROOT)
os.chdir(ROOT)  # settings read .env relative to the working directory
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from backend.db import engine  # noqa: E402  (the app's engine, built from settings.database_url)

url = engine.url
check("DATABASE_URL points at a Neon host", (url.host or "").endswith(".neon.tech"))
check("SSL is required", url.query.get("sslmode") == "require")

with engine.connect() as c:
    major = int(c.execute(text("show server_version_num")).scalar()) // 10000
    check("app engine connects; PostgreSQL 15 or newer", major >= 15, f"major version {major}")
    check("pgvector is available on the server",
          c.execute(text("select count(*) from pg_available_extensions where name = 'vector'")).scalar() == 1)

with engine.begin() as c:
    c.execute(text("create extension if not exists vector"))
with engine.connect() as c:
    check("pgvector extension is enabled", c.execute(text("select count(*) from pg_extension where extname = 'vector'")).scalar() == 1)
    c.execute(text("create temporary table t011_probe (id int, v vector(3))"))
    c.execute(text("insert into t011_probe values (1, '[1,0,0]'), (2, '[0,1,0]')"))
    nearest = c.execute(text("select id from t011_probe order by v <-> '[0.9,0.1,0]' limit 1")).scalar()
    check("vector distance query returns the nearest row", nearest == 1, f"got {nearest}")
    c.rollback()

# negative: same host and user, wrong password
bad = create_engine(url.set(password="wrong-password-for-t011"), pool_pre_ping=False, connect_args={"connect_timeout": 15})
try:
    with bad.connect():
        refused = False
except OperationalError as exc:
    refused = "password authentication failed" in str(exc)  # a network failure must not count as a refusal
finally:
    bad.dispose()
check("negative: wrong password is refused by the server", refused)

tracked = subprocess.run(["git", "ls-files", ".env"], capture_output=True, text=True).stdout.strip()
check(".env is not tracked by git", tracked == "")
compose = open("docker-compose.yml", encoding="utf-8").read()
check("docker-compose.yml keeps the local pgvector fallback", "pgvector/pgvector" in compose)

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
