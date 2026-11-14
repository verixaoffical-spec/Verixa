"""T-016 ADK skeleton, hello agent, session state in Postgres.

Asserts:
  1. The hello agent runs through the ADK Runner with ADK's DatabaseSessionService on the app's Neon database:
     its event and its state (hello_runs = 1) are stored.
  2. After a simulated restart (a new engine and a new session store), the same session is read back from
     PostgreSQL with its state and events, and a second run continues it (hello_runs = 2).
  3. ADK's tables exist in the database.
  4. The app wires the real runner to PostgreSQL: backend.analysis_service._load_runner() switches
     agents.runner to DatabaseSessionService.
  5. The real Manager + Analysis agents run through that PostgreSQL-backed runner (GitHub faked, no model keys,
     so no network and no model call) and their session events are saved.
Negative cases: a non-PostgreSQL URL keeps the in-memory store; a deleted session is gone (lookup returns None).
Every session this check creates is deleted at the end.
"""
import asyncio, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (".venv/Scripts/python.exe", ".venv/bin/python"):  # run.py uses the system python; the app needs .venv
    _venv = os.path.join(ROOT, _p)
    if os.path.exists(_venv) and os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(_venv):
        sys.exit(subprocess.run([_venv, os.path.abspath(__file__)]).returncode)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
# No model keys and no CI read: the real agents must not reach any network; trace goes to a temp file
os.environ.update({"GROQ_API_KEY": "", "OPENROUTER_API_KEY": "", "GEMINI_API_KEY": "", "GOOGLE_API_KEY": "",
                   "AGENT_CI_CHECK": "0", "AGENT_TRACE_CONSOLE": "0",
                   "AGENT_TRACE_FILE": os.path.join(tempfile.mkdtemp(), "t016-trace.jsonl")})
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


from unittest import mock  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import DatabaseSessionService, InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402
from sqlalchemy import inspect  # noqa: E402
from agents import runner  # noqa: E402
from agents.hello import hello_agent  # noqa: E402
from backend.db import engine  # noqa: E402
from backend.settings import settings  # noqa: E402

APP, USER = "verixa-t016-check", "t016"
URL = settings.database_url


async def hello_once(service, session_id=None):
    if session_id is None:
        session_id = (await service.create_session(app_name=APP, user_id=USER)).id
    msg = types.Content(role="user", parts=[types.Part(text="hello")])
    async for _ in Runner(agent=hello_agent, app_name=APP, session_service=service).run_async(
            user_id=USER, session_id=session_id, new_message=msg):
        pass
    return session_id


async def first_run():
    service = runner.session_service(URL)
    check("session store is ADK's DatabaseSessionService on PostgreSQL", isinstance(service, DatabaseSessionService))
    sid = await hello_once(service)
    s = await service.get_session(app_name=APP, user_id=USER, session_id=sid)
    check("hello agent ran: state hello_runs = 1 stored", s is not None and s.state.get("hello_runs") == 1, str(s and s.state))
    check("hello agent's event stored", s is not None and any(e.author == "hello" for e in s.events))
    await service.db_engine.dispose()
    return sid


async def after_restart(sid):
    service = runner.session_service(URL)  # a new engine and store: what a restarted server would have
    try:
        s = await service.get_session(app_name=APP, user_id=USER, session_id=sid)
        check("after restart: session read back from PostgreSQL with its state",
              s is not None and s.state.get("hello_runs") == 1 and "Hello from Verixa" in s.state.get("greeting", ""))
        await hello_once(service, sid)
        s = await service.get_session(app_name=APP, user_id=USER, session_id=sid)
        check("after restart: a second run continues the session (hello_runs = 2)", s is not None and s.state.get("hello_runs") == 2)
        check("after restart: both runs' events are in the history", s is not None and sum(e.author == "hello" for e in s.events) == 2)
    finally:  # leave nothing behind in the shared database, even when a step fails
        for x in (await service.list_sessions(app_name=APP, user_id=USER)).sessions:
            await service.delete_session(app_name=APP, user_id=USER, session_id=x.id)
    gone = await service.get_session(app_name=APP, user_id=USER, session_id=sid)
    check("negative: a deleted session is gone", gone is None)
    await service.db_engine.dispose()


sid = asyncio.run(first_run())
asyncio.run(after_restart(sid))

tables = set(inspect(engine).get_table_names())
check("ADK's session tables exist in the database", {"sessions", "events", "app_states", "user_states"} <= tables, str(sorted(tables)))

# negative: SQLite (the test database) keeps the in-memory store
saved = runner._service
runner._service = InMemorySessionService()
runner.use_database("sqlite:///unused.db")
check("negative: a non-PostgreSQL URL keeps the in-memory store", isinstance(runner._service, InMemorySessionService))
runner._service = saved

# the app's wiring, then the real agents through it
from backend import analysis_service  # noqa: E402
analysis_service._sessions_ready = False
run_manager = analysis_service._load_runner()
check("app wiring: the runner uses DatabaseSessionService", isinstance(runner._service, DatabaseSessionService))

PR_INFO = {"title": "Add token refresh", "html_url": "https://github.com/example/demo/pull/7", "user": {"login": "dev"},
           "head": {"sha": "a" * 40}, "base": {"repo": {"id": 1}}, "changed_files": 2, "additions": 40, "deletions": 3}
PR_FILES = [{"filename": "src/auth/token.ts", "additions": 30, "deletions": 2, "status": "modified",
             "patch": "+export function refresh(token) {\n+  return sign(token)\n+}"},
            {"filename": "README.md", "additions": 10, "deletions": 1, "status": "modified", "patch": "+docs"}]


async def real_agents():
    svc = runner._service
    before = {s.id for s in (await svc.list_sessions(app_name=runner.APP, user_id=runner.USER)).sessions}
    try:
        with mock.patch("agents.analysis.fetch_pr", return_value=(PR_INFO, PR_FILES)), \
             mock.patch("agents.analysis.count_fix_commits", return_value=0), \
             mock.patch("agents.analysis.count_defects", return_value=0):
            result = await run_manager("example/demo#7")
        new = [s for s in (await svc.list_sessions(app_name=runner.APP, user_id=runner.USER)).sessions if s.id not in before]
        check("real Manager + Analysis agents ran through the PostgreSQL store",
              result.get("status") in ("approved", "needs_human_review") and len(new) == 1, f"{result.get('status')}, {len(new)} new")
        s = await svc.get_session(app_name=runner.APP, user_id=runner.USER, session_id=new[0].id) if new else None
        check("their session events were saved", s is not None and len(s.events) > 0, f"{len(s.events) if s else 'none'} events")
    finally:  # delete only the sessions this check made
        for x in (await svc.list_sessions(app_name=runner.APP, user_id=runner.USER)).sessions:
            if x.id not in before:
                await svc.delete_session(app_name=runner.APP, user_id=runner.USER, session_id=x.id)
    await svc.db_engine.dispose()


asyncio.run(real_agents())

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
