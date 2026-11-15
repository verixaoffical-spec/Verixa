"""The one table the Analysis Agent owns: `risk_assessments`.

New in this consolidated app. It lives in the same database and on the same engine as the five
tables backend/db.py owns, and it does not add a single column to any of them, which is the rule
the Official UI README sets for agent work.

It carries its own declarative base so `init_db()` (app tables) and `init_agent_db()` (agent
tables) stay separate and obvious.

Mapping to docs/DATA_MODEL.md: that document splits this into `pull_requests` and
`risk_assessments`. The consolidated scope is risk scoring only, so the handful of pull request
facts the dashboard shows (title, author, url, head sha) are folded into this one row. When the
Test Agent lands in Deliverable 3 and needs a real run object, split it then.
"""
import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .db import Project, engine, now

# How far a pull request has got. `scored` and `needs_human_review` are terminal and come straight
# from the Analysis Manager's own verdict; `failed` means the agent could not run at all.
STATES = ("queued", "running", "scored", "needs_human_review", "failed")

# The column the foreign key points at, as the real Column object rather than the string
# "projects.id". A string is looked up inside the declaring base's own MetaData, and this base has
# its own, so the string would never resolve. Pointing at the column directly keeps the two sets of
# tables in separate metadata while still emitting REFERENCES projects (id).
PROJECT_ID = Project.__table__.c.id


class AgentBase(DeclarativeBase):
    """Separate from backend.db.Base on purpose: the app's five tables and the agent's table are
    created, dropped and fingerprinted independently."""


class RiskAssessment(AgentBase):
    """One row per (project, pull request, head commit). A new push to the same PR is a new row,
    so the history of how the risk moved is kept rather than overwritten."""
    __tablename__ = "risk_assessments"
    __table_args__ = (UniqueConstraint("project_id", "pr_number", "head_sha", name="uq_risk_pr_head"),
                      Index("ix_risk_feed", "project_id", "repo", "created_at"))  # T-094: the Risk feed's own query

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECT_ID), index=True)
    repo: Mapped[str] = mapped_column(String(200), index=True)
    pr_number: Mapped[int]
    head_sha: Mapped[str] = mapped_column(String(64))

    # Pull request facts, taken from the webhook payload so the row is useful before the agent runs
    title: Mapped[str | None] = mapped_column(String(500))
    pr_url: Mapped[str | None] = mapped_column(String(500))
    author: Mapped[str | None] = mapped_column(String(100))
    delivery_id: Mapped[str | None] = mapped_column(String(100))  # X-GitHub-Delivery, to spot repeats

    state: Mapped[str] = mapped_column(String(24), default="queued")

    # Rule output (risk_rules.assess). The label is decided in code, never by a model.
    risk_label: Mapped[str | None] = mapped_column(String(10))
    base_label: Mapped[str | None] = mapped_column(String(10))  # before the minimum-label floors
    score: Mapped[int | None]
    module: Mapped[str | None] = mapped_column(String(200))
    modules_touched: Mapped[str | None] = mapped_column(Text)   # JSON list
    files_changed: Mapped[int | None]
    lines_changed: Mapped[int | None]
    past_defects: Mapped[int | None]
    sensitivity: Mapped[str | None] = mapped_column(String(10))
    scoring_basis: Mapped[str | None] = mapped_column(String(200))
    risk_factors: Mapped[str | None] = mapped_column(Text)      # JSON list

    # Model output, written only after the Manager accepted it
    reasoning: Mapped[str | None] = mapped_column(Text)
    test_areas: Mapped[str | None] = mapped_column(Text)        # JSON list
    model_used: Mapped[str | None] = mapped_column(String(120))
    concern: Mapped[str | None] = mapped_column(Text)            # the model's doubt about the rule label, if any

    # Manager bookkeeping (T-035): how many attempts it took, and why it gave up
    attempts: Mapped[int] = mapped_column(default=0)
    errors: Mapped[str | None] = mapped_column(Text)            # JSON list

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class ModelCall(AgentBase):
    """One row per model attempt (T-026): which model answered or failed, how fast, how many tokens. Written from
    the agents' trace by backend/model_calls.py; used for quota tracking and model evals (docs/MODELS.md)."""
    __tablename__ = "model_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent: Mapped[str] = mapped_column(String(40))          # the chain's task: analysis, select, classify, draft
    model: Mapped[str] = mapped_column(String(120))         # provider/model, as in backend/llm/config.yaml
    provider: Mapped[str] = mapped_column(String(40))       # groq, openrouter, gemini
    tokens: Mapped[int | None]
    latency_ms: Mapped[int | None]
    ok: Mapped[bool]
    error: Mapped[str | None] = mapped_column(Text)          # masked, first 300 characters
    run_id: Mapped[str | None] = mapped_column(String(40), index=True)  # the agents' trace run, when there is one
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class PrFileSnapshot(AgentBase):
    """T-094: a pull request's changed files at one analysed commit, with a risk each and the imports between them
    (backend/pr_files.py). A commit never changes, so it is read from GitHub once and served from here afterwards."""
    __tablename__ = "pr_file_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey(RiskAssessment.__table__.c.id, ondelete="CASCADE"), unique=True)
    head_sha: Mapped[str] = mapped_column(String(64))
    data: Mapped[str] = mapped_column(Text)                 # the /files answer as JSON, with its rules version
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AgentStep(AgentBase):
    """T-094: one step of an agent run, as the live view shows it (backend/live.py describe). Written from the trace
    by backend/model_calls.py (record_step), so a run's history outlives the rotating trace file."""
    __tablename__ = "agent_steps"
    __table_args__ = (Index("ix_agent_steps_pr", "repo", "pr_number", "at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    repo: Mapped[str] = mapped_column(String(200))
    pr_number: Mapped[int]
    run_id: Mapped[str | None] = mapped_column(String(40))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event: Mapped[str] = mapped_column(String(60))
    stage: Mapped[str] = mapped_column(String(20))
    level: Mapped[str] = mapped_column(String(10))
    text: Mapped[str] = mapped_column(Text)
    done: Mapped[bool]



class PullRequest(AgentBase):
    """T-096: every pull request of a connected repository, analysed or not, as GitHub lists it. Filled by
    backend/pull_requests.py from GitHub's pull request list and from each webhook delivery, so the Pull Requests
    screen reads the database and GitHub is only asked again when the list is stale."""
    __tablename__ = "pull_requests"
    __table_args__ = (UniqueConstraint("project_id", "number", name="uq_pull_requests_project_number"),
                      Index("ix_pull_requests_feed", "project_id", "gh_updated_at"))

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey(PROJECT_ID, ondelete="CASCADE"))
    repo: Mapped[str] = mapped_column(String(200))
    number: Mapped[int]
    title: Mapped[str | None] = mapped_column(String(500))
    author: Mapped[str | None] = mapped_column(String(100))          # GitHub login of who opened it
    state: Mapped[str] = mapped_column(String(10))                   # open, closed or merged
    draft: Mapped[bool] = mapped_column(default=False)
    html_url: Mapped[str | None] = mapped_column(String(500))
    head_sha: Mapped[str | None] = mapped_column(String(64))
    gh_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gh_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    listed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # last seen in GitHub's list; staleness

def init_agent_db() -> None:
    """Creates `risk_assessments` if it is not there, and adds columns introduced later. Never drops anything."""
    AgentBase.metadata.create_all(engine)
    columns = {c["name"] for c in inspect(engine).get_columns("risk_assessments")}
    if "concern" not in columns:  # added 7 November 2026, for the model's doubt about a rule label
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE risk_assessments ADD COLUMN concern TEXT"))


def agent_tables() -> list[str]:
    """The agent-owned tables that exist right now. scripts/check_database.py uses this."""
    present = set(inspect(engine).get_table_names())
    return [t for t in ("risk_assessments", "test_runs", "test_results", "test_drafts") if t in present]


def _load(raw: str | None, fallback):
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except ValueError:
        return fallback


def dump(value) -> str | None:
    """Stores a list as JSON text. SQLite and PostgreSQL both take it unchanged."""
    return None if value is None else json.dumps(value)


def _iso(at: datetime | None) -> str | None:
    """SQLite loses the timezone, and a browser reads a time without one as local. Every time here is UTC."""
    if at is None:
        return None
    return (at if at.tzinfo else at.replace(tzinfo=timezone.utc)).isoformat()


def to_json(row: RiskAssessment) -> dict:
    """The shape the dashboard reads. Keys are snake_case, like the rest of the API."""
    return {
        "id": row.id,
        "repo": row.repo,
        "pr_number": row.pr_number,
        "head_sha": row.head_sha,
        "title": row.title,
        "pr_url": row.pr_url,
        "author": row.author,
        "state": row.state,
        "risk_label": row.risk_label,
        "base_label": row.base_label,
        "score": row.score,
        "module": row.module,
        "modules_touched": _load(row.modules_touched, []),
        "files_changed": row.files_changed,
        "lines_changed": row.lines_changed,
        "past_defects": row.past_defects,
        "sensitivity": row.sensitivity,
        "scoring_basis": row.scoring_basis,
        "risk_factors": _load(row.risk_factors, []),
        "reasoning": row.reasoning,
        "test_areas": _load(row.test_areas, []),
        "model_used": row.model_used,
        "concern": row.concern or None,
        "attempts": row.attempts,
        "errors": _load(row.errors, []),
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }
