"""T-026 LLM router: config.yaml, fallback, model_calls logging.

Live calls on Groq (approved by the owner), tiny prompts; keys come from .env and are never printed.
Asserts:
  1. backend/llm/config.yaml holds the chains, agents.llm reads them from there, and no model name from it is
     written anywhere in the app's Python code (CLAUDE.md: model names live only in config.yaml).
  2. A chain can still be overridden with <TASK>_MODELS.
  3. Fallback through agents.llm.ask: a failing first model, then the next one answers; each attempt becomes one
     model_calls row (failed row with provider and error; answered row with tokens and latency).
  4. The real Manager + Analysis agents (GitHub faked, live Groq) log their model call to model_calls with tokens.
Negative cases: a malformed config.yaml is refused at load; when model_calls cannot be written, the model answer
still comes back (logging never breaks an analysis).
Every row and session this check creates is deleted.
"""
import asyncio, os, pathlib, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (".venv/Scripts/python.exe", ".venv/bin/python"):  # run.py uses the system python; the app needs .venv
    _venv = os.path.join(ROOT, _p)
    if os.path.exists(_venv) and os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(_venv):
        sys.exit(subprocess.run([_venv, os.path.abspath(__file__)]).returncode)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.update({"AGENT_CI_CHECK": "0", "AGENT_TRACE_CONSOLE": "0",
                   "AGENT_TRACE_FILE": os.path.join(tempfile.mkdtemp(), "t026-trace.jsonl")})
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


import backend  # noqa: E402,F401  (loads .env into the environment, as the app does)
import yaml  # noqa: E402
from unittest import mock  # noqa: E402
from sqlalchemy import delete, func, select  # noqa: E402
from agents import llm, runner  # noqa: E402
from agents.trace import add_listener  # noqa: E402
from backend import analysis_service, model_calls  # noqa: E402
from backend.agent_db import ModelCall  # noqa: E402
from backend.db import SessionLocal  # noqa: E402

# 1. config.yaml is the source of the chains, and the code holds no model name
cfg = yaml.safe_load(pathlib.Path("backend/llm/config.yaml").read_text(encoding="utf-8"))["chains"]
check("config.yaml has the analysis, select, classify and draft chains", set(cfg) == {"analysis", "select", "classify", "draft"})
check("agents.llm reads its chains from config.yaml", llm.DEFAULT_CHAINS == cfg)
names = {m for chain in cfg.values() for m in chain} | {m.split("/", 1)[1] for chain in cfg.values() for m in chain}
code = [p for d in ("agents", "backend") for p in pathlib.Path(d).rglob("*.py") if "migrations" not in p.parts]
found = [(str(p), n) for p in code for n in names if f'"{n}"' in p.read_text(encoding="utf-8") or f"'{n}'" in p.read_text(encoding="utf-8")]
check("no model name from config.yaml is hardcoded in agents/ or backend/ Python code", not found, str(found[:4]))

# 2. env override
with mock.patch.dict(os.environ, {"ANALYSIS_MODELS": "groq/a, groq/b"}):
    check("ANALYSIS_MODELS still overrides the chain", llm.chain("analysis") == ["groq/a", "groq/b"])

# negative: malformed config
bad = pathlib.Path(tempfile.mkdtemp()) / "config.yaml"
bad.write_text("chains:\n  analysis: []\n", encoding="utf-8")
try:
    llm.load_chains(bad)
    refused = False
except ValueError:
    refused = True
check("negative: a config with an empty chain is refused", refused)

# 3. fallback and model_calls rows
add_listener(model_calls.record)
GROQ, BAD = cfg["analysis"][0], "groq/verixa-no-such-model"
with SessionLocal() as db:
    start_id = db.scalar(select(func.coalesce(func.max(ModelCall.id), 0)))
try:
    with mock.patch.dict(os.environ, {"ANALYSIS_MODELS": f"{BAD},{GROQ}"}):
        answer, used = asyncio.run(llm.ask("analysis", "Answer only with JSON.", 'Return {"ok": true}'))
    check("fallback: the failing model is skipped and the next one answers with parsed JSON", used == GROQ and answer == {"ok": True},
          f"{used} {answer!r}")
    check("model_calls writer drained", model_calls.flush(20))
    with SessionLocal() as db:
        rows = db.scalars(select(ModelCall).where(ModelCall.id > start_id).order_by(ModelCall.id)).all()
    failed = [r for r in rows if r.model == BAD]
    okrow = [r for r in rows if r.model == GROQ and r.ok]
    check("failed attempt logged: ok=false, provider groq, error kept",
          len(failed) == 1 and not failed[0].ok and failed[0].provider == "groq" and bool(failed[0].error), str([(r.model, r.ok) for r in rows]))
    check("answered attempt logged: ok=true with tokens and latency",
          len(okrow) == 1 and (okrow[0].tokens or 0) > 0 and (okrow[0].latency_ms or 0) > 0,
          str([(r.model, r.ok, r.tokens, r.latency_ms) for r in okrow]))

    # negative: the database refuses the row, the answer still comes back
    with mock.patch.object(model_calls, "SessionLocal", side_effect=OSError("db down")):
        answer, used = asyncio.run(llm.ask("analysis", "Answer only with JSON.", 'Return {"ok": true}'))
        model_calls.flush(20)
    check("negative: when model_calls cannot be written, the answer still comes back", answer == {"ok": True})

    # 4. the real agents log their call
    PR_INFO = {"title": "Add token refresh", "html_url": "https://github.com/example/demo/pull/9", "user": {"login": "dev"},
               "head": {"sha": "b" * 40}, "base": {"repo": {"id": 1}}, "changed_files": 1, "additions": 12, "deletions": 1}
    PR_FILES = [{"filename": "src/auth/token.ts", "additions": 12, "deletions": 1, "status": "modified",
                 "patch": "+export function refresh(token) {\n+  return sign(token)\n+}"}]
    analysis_service._sessions_ready = False
    run_manager = analysis_service._load_runner()

    async def agents_run():
        svc = runner._service
        before = {s.id for s in (await svc.list_sessions(app_name=runner.APP, user_id=runner.USER)).sessions}
        try:
            with mock.patch("agents.analysis.fetch_pr", return_value=(PR_INFO, PR_FILES)), \
                 mock.patch("agents.analysis.count_fix_commits", return_value=0), \
                 mock.patch("agents.analysis.count_defects", return_value=0):
                return await run_manager("example/demo#9")
        finally:
            for s in (await svc.list_sessions(app_name=runner.APP, user_id=runner.USER)).sessions:
                if s.id not in before:
                    await svc.delete_session(app_name=runner.APP, user_id=runner.USER, session_id=s.id)
            if hasattr(svc, "db_engine"):
                await svc.db_engine.dispose()

    with SessionLocal() as db:
        mark = db.scalar(select(func.coalesce(func.max(ModelCall.id), 0)))
    result = asyncio.run(agents_run())
    model_calls.flush(20)
    with SessionLocal() as db:
        rows = db.scalars(select(ModelCall).where(ModelCall.id > mark, ModelCall.agent == "analysis")).all()
    check("real agents: their model call is in model_calls with tokens and the run id",
          any(r.ok and (r.tokens or 0) > 0 and r.run_id == result.get("run_id") for r in rows),
          f"status {result.get('status')}, rows {[(r.model, r.ok, r.tokens) for r in rows]}")
finally:
    model_calls.flush(20)
    with SessionLocal() as db:  # leave nothing behind, and touch only rows for the models this check called
        db.execute(delete(ModelCall).where(ModelCall.id > start_id, ModelCall.model.in_(set(cfg["analysis"]) | {BAD})))
        db.commit()

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
