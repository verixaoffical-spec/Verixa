"""JSON API for the Risk Analysis screen: `/api/analysis`.

Reads the rows the Analysis Agent wrote and, on request, asks it to score a pull request now.
Every route needs an account, through the same `current_user` dependency the rest of the dashboard
uses, so the session cookie and the 401 contract ("the session is gone") are unchanged.
"""
import json
import logging
from typing import Any

import httpx
from importlib.util import find_spec

from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .agent_db import AgentStep, PrFileSnapshot, RiskAssessment, _iso, to_json
from .analysis_service import AgentUnavailable, analyse_now
from .api import MAX_INT, current_user, project_of
from .auth import _check_origin
from .db import User, get_db
from .integrations import github_access_token
from .live import describe
from .pr_files import SNAPSHOT_VERSION, group_runs, pr_files, pr_log
from . import pull_requests as repo_pulls
from .accounts import Throttle

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analysis")

LABELS = ("High", "Medium", "Low")
LOG_STEPS = 2000  # newest steps of one PR shown in its log
forced_lists = Throttle(limit=6, window=60)  # T-096: "Refresh from GitHub" cannot burn the account's GitHub quota


@router.get("/pull-requests")
def pull_requests(limit: int = Query(50, ge=1, le=200),
                  user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Every pull request the agent has looked at for this account's project, newest first.

    No project connected is not an error: the screen shows its own "connect a repository first"
    state, the same way the Test Library does.
    """
    project = project_of(db, user)
    if not project:
        return {"project": None, "items": [], "counts": {}, "agent_available": find_spec("google.adk") is not None}

    # Only the repository connected now: rows from before switching repository are kept, but they are not this screen's.
    mine = (RiskAssessment.project_id == project.id, RiskAssessment.repo == project.repo)
    newest_first = (RiskAssessment.created_at.desc(), RiskAssessment.id.desc())
    rows = db.scalars(select(RiskAssessment).where(*mine).order_by(*newest_first).limit(limit)).all()

    # Counts are over the latest assessment per pull request, so one PR pushed to five times is
    # counted once, at its current risk. They cover every row, whatever the page size.
    latest: dict[int, Any] = {}
    for row in db.execute(select(RiskAssessment.pr_number, RiskAssessment.risk_label, RiskAssessment.state)
                          .where(*mine).order_by(*newest_first)):
        latest.setdefault(row.pr_number, row)
    counts = {label: 0 for label in LABELS}
    for row in latest.values():
        if row.risk_label in counts:
            counts[row.risk_label] += 1

    return {
        "project": {"repo": project.repo, "jira_key": project.jira_key,
                    "webhook_verified": bool(project.webhook_verified_at)},
        "items": [to_json(row) for row in rows],
        "counts": {
            **counts,
            "total": len(latest),
            "pending": sum(1 for r in latest.values() if r.state in ("queued", "running")),
            "scored": sum(1 for r in latest.values() if r.state == "scored"),  # T-036: every status slice from one source
            "needs_review": sum(1 for r in latest.values() if r.state == "needs_human_review"),
            "failed": sum(1 for r in latest.values() if r.state == "failed"),
        },
        "agent_available": find_spec("google.adk") is not None,
    }


@router.get("/pull-requests/{assessment_id}")
def one_assessment(assessment_id: int = Path(ge=1, le=MAX_INT), user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    """One assessment in full. 404 for a row that belongs to somebody else, never 403, so the id
    space of another account cannot be probed."""
    project = project_of(db, user)
    row = db.get(RiskAssessment, assessment_id) if project else None
    if not row or not project or row.project_id != project.id:
        raise HTTPException(404, "No analysis with that id")
    return to_json(row)


def _own_row(db: Session, user: User, assessment_id: int) -> RiskAssessment:
    project = project_of(db, user)
    row = db.get(RiskAssessment, assessment_id) if project else None
    if not row or not project or row.project_id != project.id:
        raise HTTPException(404, "No analysis with that id")
    return row


@router.get("/pull-requests/{assessment_id}/files")
async def changed_files(assessment_id: int = Path(ge=1, le=MAX_INT), user: User = Depends(current_user),
                        db: Session = Depends(get_db)):
    """T-038: the pull request's changed files with a risk each and the imports between them, read from GitHub now."""
    row = _own_row(db, user, assessment_id)
    saved = db.scalar(select(PrFileSnapshot).where(PrFileSnapshot.assessment_id == row.id))
    # T-094: a commit never changes, so its files are read from GitHub only once. The first read decides: a PR still on
    # the analysed commit is saved; one that already moved on is shown at its newer commit and never saved.
    cached = json.loads(saved.data) if saved else None
    if cached and cached.get("version") == SNAPSHOT_VERSION:  # older rules: read again and replace
        return {**cached, "cached": True}
    if not user.github_token:
        raise HTTPException(409, "Link GitHub first, so Verixa can read the pull request")
    try:
        token = await run_in_threadpool(github_access_token, db, user)
    except InvalidToken:
        raise HTTPException(409, "Your stored GitHub token could not be read. Link GitHub again")
    try:
        data = await run_in_threadpool(pr_files, row.repo, row.pr_number, row.head_sha, token)
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        raise HTTPException(502, "GitHub has no such pull request any more" if code == 404 else
                            f"GitHub refused to list the changed files ({code})")
    except httpx.HTTPError:
        raise HTTPException(502, "Could not reach GitHub")
    data["version"] = SNAPSHOT_VERSION
    if data["same_commit"]:  # only the analysed commit is fixed; a PR that moved on may move again
        try:
            if saved:
                saved.data, saved.head_sha = json.dumps(data), row.head_sha
            else:
                db.add(PrFileSnapshot(assessment_id=row.id, head_sha=row.head_sha, data=json.dumps(data)))
            db.commit()
        except SQLAlchemyError as exc:  # two tabs saved it at once, or the database hiccuped: the answer is still good
            db.rollback()
            log.info("pr_file_snapshots: not saved for %s (%s)", row.id, type(exc).__name__)
    return {**data, "cached": False}


@router.get("/pull-requests/{assessment_id}/log")
def past_log(assessment_id: int = Path(ge=1, le=MAX_INT), user: User = Depends(current_user),
             db: Session = Depends(get_db)):
    """Every saved run of this pull request, newest first: from agent_steps (T-094), or from the trace log for runs
    from before agent_steps existed."""
    row = _own_row(db, user, assessment_id)
    steps = db.scalars(select(AgentStep).where(AgentStep.repo == row.repo, AgentStep.pr_number == row.pr_number)
                       .order_by(AgentStep.at.desc(), AgentStep.id.desc()).limit(LOG_STEPS)).all()[::-1]  # the newest
    if not steps:  # runs from before agent_steps existed (D-013: once a PR has saved steps, only those are shown)
        return {"runs": pr_log(row.repo, row.pr_number, describe)}
    return {"runs": group_runs([{"type": "agent", "repo": s.repo, "pr": s.pr_number, "run_id": s.run_id, "at": _iso(s.at),
                                 "event": s.event, "text": s.text, "level": s.level, "done": s.done, "stage": s.stage}
                                for s in steps])}


class AnalyseIn(BaseModel):
    pr_number: int = Field(strict=True, ge=1, le=10_000_000)  # strict: true and "4" are not pull request numbers


@router.get("/repo-pulls")
def repo_pull_list(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """T-096: every saved pull request of the connected repository with its author, newest activity first. Reads the
    database only; `stale` tells the screen to ask for a refresh (POST /repo-pulls/sync) in the background."""
    project = project_of(db, user)
    if not project:
        return {"listed_at": None, "stale": False, "items": []}
    return repo_pulls.rows_json(db, project)


@router.post("/repo-pulls/sync")
async def repo_pull_sync(request: Request, force: bool = Query(False), user: User = Depends(current_user),
                         db: Session = Depends(get_db)):
    """Reads GitHub's pull request list and saves it, unless the saved one is still fresh and no refresh was forced."""
    _check_origin(request)
    project = project_of(db, user)
    if not project:
        raise HTTPException(409, "Connect a repository first")
    if not force and not repo_pulls.is_stale(db, project):
        return repo_pulls.rows_json(db, project)
    if force:
        if wait := forced_lists.retry_after(str(user.id)):
            raise HTTPException(429, f"Refreshed too often. Try again in {wait} seconds")
        forced_lists.fail(str(user.id))
    if not user.github_token:
        raise HTTPException(409, "Link GitHub first, so Verixa can list the pull requests")
    try:
        token = await run_in_threadpool(github_access_token, db, user)
    except InvalidToken:
        raise HTTPException(409, "Your stored GitHub token could not be read. Link GitHub again")
    try:
        await run_in_threadpool(repo_pulls.sync, db, project, token)
    except httpx.HTTPStatusError as exc:
        db.rollback()
        raise HTTPException(502, f"GitHub refused to list the pull requests ({exc.response.status_code})")
    except httpx.HTTPError:
        db.rollback()
        raise HTTPException(502, "Could not reach GitHub")
    return repo_pulls.rows_json(db, project)


@router.post("/analyse")
async def analyse(body: AnalyseIn, request: Request, user: User = Depends(current_user),
                  db: Session = Depends(get_db)):
    """Scores a pull request now, instead of waiting for GitHub to deliver an event.

    This is how a tester re-runs the analysis after a failure, and how the flow is tested without
    a public tunnel. It runs the agent inline and answers when it is done, which takes as long as
    the model chain takes: it is a dashboard call, not a webhook, so there is no 10 second limit.
    """
    _check_origin(request)
    project = project_of(db, user)
    if not project:
        raise HTTPException(409, "Connect a repository first")
    if not user.github_token:
        raise HTTPException(409, "Link GitHub first, so Verixa can read the pull request")

    try:
        token = await run_in_threadpool(github_access_token, db, user)
    except InvalidToken:
        raise HTTPException(409, "Your stored GitHub token could not be read. Link GitHub again")

    try:
        row_id = await analyse_now(project, body.pr_number, token)
    except AgentUnavailable as exc:
        raise HTTPException(503, str(exc))
    except ValueError as exc:
        raise HTTPException(502, str(exc))
    except Exception as exc:
        log.exception("on-demand analysis of %s#%s failed", project.repo, body.pr_number)
        raise HTTPException(500, f"The analysis failed: {type(exc).__name__}")

    row = db.get(RiskAssessment, row_id)
    if not row:
        raise HTTPException(500, "The analysis produced no result")
    db.refresh(row)
    return to_json(row)
