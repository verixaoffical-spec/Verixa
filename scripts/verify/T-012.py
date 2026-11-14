"""T-012 Initial schema and migrations.

Asserts:
  1. `alembic upgrade head` runs on the app's database (Neon, from .env) and leaves it at the head revision.
  2. The database holds exactly mid's eight tables (+ alembic_version), and every table matches the app's models
     (backend.db.Base + backend.agent_db.AgentBase, byte-identical to mid since T-010): columns, nullability,
     primary keys, foreign keys and unique constraints (test case TC-03).
  3. `alembic check` finds no difference between the models and the migrated database.
  4. The migration round trip works on a throwaway SQLite file: upgrade creates the eight tables, downgrade removes them.
  5. pgvector stays enabled on the database.
  6. The real app works on the new database: scripts/check_database.py signs up a temporary account, uses every
     table, deletes it, and proves the agent table did not change.
Negative case: the schema comparison flags a database where one column is missing.
"""
import os, subprocess, sys, tempfile

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


from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from alembic.util.exc import CommandError  # noqa: E402
from sqlalchemy import create_engine, inspect, text  # noqa: E402
from backend.agent_db import AgentBase  # noqa: E402
from backend.db import Base, engine  # noqa: E402

MID_TABLES = {"users", "recovery_codes", "password_resets", "pending_signups", "projects", "spec_files", "collections",
              "risk_assessments"}
MODELS = {t.name: t for md in (Base.metadata, AgentBase.metadata) for t in md.sorted_tables}
# Every table the app's models define (mid's eight, plus later migrations such as model_calls in T-026)
TABLES = set(MODELS)
check("mid's eight tables are all still in the app's models", MID_TABLES <= TABLES, str(sorted(MID_TABLES - TABLES)))
# ADK's DatabaseSessionService creates and manages its own tables (T-016); they are not part of these migrations
ADK_TABLES = {"sessions", "events", "app_states", "user_states", "adk_internal_metadata"}
check("no app table shares a name with ADK's tables (so the exclusion hides nothing of ours)", not ADK_TABLES & MODELS.keys())


def cfg(url: str | None = None) -> Config:
    c = Config(os.path.join(ROOT, "alembic.ini"))
    c.attributes["configure_logger"] = False
    if url:
        c.set_main_option("sqlalchemy.url", url)
    return c


def schema_problems(eng) -> list[str]:
    """Differences between a live database and the models, table by table."""
    insp, out = inspect(eng), []
    live = set(insp.get_table_names()) - {"alembic_version"} - ADK_TABLES
    out += [f"missing table {t}" for t in sorted(TABLES - live)] + [f"extra table {t}" for t in sorted(live - TABLES)]
    for name in sorted(TABLES & live):
        model, cols = MODELS[name], {c["name"]: c for c in insp.get_columns(name)}
        for col in model.columns:
            if col.name not in cols:
                out.append(f"{name}.{col.name} missing")
            elif bool(cols[col.name]["nullable"]) != bool(col.nullable):
                out.append(f"{name}.{col.name} nullable is {cols[col.name]['nullable']}, model says {col.nullable}")
        out += [f"{name}.{c} not in the model" for c in cols if c not in model.columns]
        if set(insp.get_pk_constraint(name)["constrained_columns"]) != {c.name for c in model.primary_key}:
            out.append(f"{name} primary key differs")
        live_fk = {(tuple(f["constrained_columns"]), f["referred_table"]) for f in insp.get_foreign_keys(name)}
        model_fk = {(tuple(e.parent.name for e in f.elements), f.elements[0].column.table.name) for f in model.foreign_key_constraints}
        if live_fk != model_fk:
            out.append(f"{name} foreign keys {sorted(live_fk)} != model {sorted(model_fk)}")
        live_uq = {tuple(sorted(u["column_names"])) for u in insp.get_unique_constraints(name)}
        live_uq |= {tuple(sorted(i["column_names"])) for i in insp.get_indexes(name) if i.get("unique")}
        model_uq = {tuple(sorted(c.name for c in u.columns)) for u in model.constraints if u.__class__.__name__ == "UniqueConstraint"}
        model_uq |= {(c.name,) for c in model.columns if c.unique}
        if not model_uq <= live_uq:
            out.append(f"{name} unique constraints missing: {sorted(model_uq - live_uq)}")
    return out


# 1. migrate the real database
head = ScriptDirectory.from_config(cfg()).get_current_head()
command.upgrade(cfg(), "head")
with engine.connect() as c:
    current = c.execute(text("select version_num from alembic_version")).scalar()
check(f"database is at the head revision ({head})", current == head, f"at {current}")

# 2. exactly mid's tables, matching the models
problems = schema_problems(engine)
check("database has every model table (mid's 8 + later) and matches the models (TC-03)", not problems, "; ".join(problems[:6]))

# 3. models and migrations agree
try:
    command.check(cfg())
    check("alembic check: no difference between models and database", True)
except CommandError as exc:
    check("alembic check: no difference between models and database", False, str(exc)[:300])

# 4. round trip on a throwaway SQLite file, never on the shared database
tmp = tempfile.mkdtemp()
lite_url = "sqlite:///" + os.path.join(tmp, "t012.db").replace("\\", "/")
command.upgrade(cfg(lite_url), "head")
lite = create_engine(lite_url)
check("round trip: upgrade creates every model table", set(inspect(lite).get_table_names()) - {"alembic_version"} == TABLES)
check("round trip: SQLite copy matches the models too", not schema_problems(lite), "; ".join(schema_problems(lite)[:4]))

# negative: the comparison catches a missing column
with lite.begin() as c:
    c.execute(text("alter table projects drop column jira_name"))
found = schema_problems(lite)
check("negative: a missing column is flagged", any("projects.jira_name missing" in p for p in found), str(found))
lite.dispose()
command.downgrade(cfg(lite_url), "base")
lite = create_engine(lite_url)
check("round trip: downgrade removes the tables", set(inspect(lite).get_table_names()) - {"alembic_version"} == set())
lite.dispose()

# 5. pgvector
with engine.connect() as c:
    check("pgvector still enabled", c.execute(text("select count(*) from pg_extension where extname = 'vector'")).scalar() == 1)

# 6. the real app on the new database (temporary account, cleaned up, agent table unchanged)
r = subprocess.run([sys.executable, "-m", "scripts.check_database"], capture_output=True, text=True, timeout=600)
print("     " + " | ".join(l.strip() for l in r.stdout.splitlines() if l.strip().startswith("ok"))[:600])
check("app check on the new database passes (scripts/check_database.py)",
      r.returncode == 0 and "agent tables unchanged" in r.stdout, (r.stdout + r.stderr)[-400:])

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
