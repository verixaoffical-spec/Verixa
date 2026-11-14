# The tests use their own database, never the one in .env. Set TEST_DATABASE_URL to run them on PostgreSQL.
import os
import tempfile

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or (
    "sqlite:///" + os.path.join(tempfile.gettempdir(), "verixa-tests.db").replace("\\", "/"))
os.environ["PUBLIC_URL"] = "http://testserver"
# The agents' trace stays out of the real log and out of the test output.
os.environ["AGENT_TRACE_FILE"] = os.path.join(tempfile.gettempdir(), "verixa-tests-trace.jsonl")
os.environ["AGENT_TRACE_CONSOLE"] = "0"
# The agent's CI read calls GitHub, so it is off unless a test turns it on and fakes GitHub.
os.environ["AGENT_CI_CHECK"] = "0"
for name in ("SECRET_KEY", "WEBHOOK_SECRET", "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET",
             "ATLASSIAN_CLIENT_ID", "ATLASSIAN_CLIENT_SECRET"):
    os.environ.setdefault(name, "test-value-for-" + name.lower())

# T-094: model_calls and agent_steps rows are written on a background thread. Wait for queued rows before any test
# drops the tables, so a late write never races the drop (SQLite "database is locked" or "no such table").
from sqlalchemy import MetaData  # noqa: E402

_drop_all = MetaData.drop_all


def _drop_all_after_writes(self, *args, **kwargs):
    from backend import model_calls  # imported late: the settings above must be in place first
    model_calls.flush(5)
    return _drop_all(self, *args, **kwargs)


MetaData.drop_all = _drop_all_after_writes
