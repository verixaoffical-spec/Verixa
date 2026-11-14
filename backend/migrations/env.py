"""Alembic environment: the app's two sets of tables, on the app's own database.

backend.db.Base owns the seven account and Test Library tables; backend.agent_db.AgentBase owns
risk_assessments. Both are compared, so a migration covers all eight.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from backend.agent_db import AgentBase
from backend.db import Base
from backend.settings import settings

config = context.config
if config.config_file_name and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = [Base.metadata, AgentBase.metadata]
url = config.get_main_option("sqlalchemy.url") or settings.database_url

# Created and migrated by ADK's DatabaseSessionService (T-016), not by these migrations
ADK_TABLES = {"sessions", "events", "app_states", "user_states", "adk_internal_metadata"}
_ours = {t.name for md in target_metadata for t in md.sorted_tables}
assert not ADK_TABLES & _ours, f"an app table has an ADK table name and would be skipped: {ADK_TABLES & _ours}"


def include_object(obj, name, type_, reflected, compare_to):
    table = obj if type_ == "table" else getattr(obj, "table", None)
    return getattr(table, "name", name) not in ADK_TABLES


def run_migrations_offline() -> None:
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True,
                      include_object=include_object)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True,
                          include_object=include_object,
                          render_as_batch=connection.dialect.name == "sqlite")
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
