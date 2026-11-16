"""T-096: every pull request of the connected repository, with who opened it, saved in pull_requests.

GitHub's list is read only when the saved one is stale (LIST_TTL) or a person asks for a refresh, never on every
screen open. Each webhook delivery also writes its pull request, so a new one shows up without a list read.
"""
from datetime import datetime, timedelta

import httpx
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agents.github_client import API, _headers

from .agent_db import PullRequest, RiskAssessment, _iso
from .db import Project, now

LIST_TTL = timedelta(minutes=5)  # an older list is read again from GitHub
MAX_PAGES = 3                    # 300 most recently updated pull requests; older ones stay as last saved
GITHUB_URL = "https://github.com/"


def _text(value, limit: int) -> str | None:
    return value[:limit] if isinstance(value, str) and value else None


def _when(value) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else None
    except ValueError:
        return None


def facts_of(pr: dict) -> dict | None:
    """The saved columns of one pull request as GitHub describes it (the list API and webhook payloads agree)."""
    number = pr.get("number")
    if type(number) is not int or number < 1:
        return None
    user: dict = pr["user"] if isinstance(pr.get("user"), dict) else {}
    head: dict = pr["head"] if isinstance(pr.get("head"), dict) else {}
    base: dict = pr["base"] if isinstance(pr.get("base"), dict) else {}
    url = _text(pr.get("html_url"), 500)
    return {
        "number": number,
        "title": _text(pr.get("title"), 500),
        "author": _text(user.get("login"), 100),
        "state": "merged" if pr.get("merged_at") else ("closed" if pr.get("state") == "closed" else "open"),
        "draft": pr.get("draft") is True,
        "html_url": url if url and url.startswith(GITHUB_URL) else None,  # the screen makes it a link, so never javascript:
        "head_sha": _text(head.get("sha"), 64),
        "head_ref": _text(head.get("ref"), 255),  # T-099: source branch
        "base_ref": _text(base.get("ref"), 255),  # T-099: target branch
        "gh_created_at": _when(pr.get("created_at")),
        "gh_updated_at": _when(pr.get("updated_at")),
    }


def save(db: Session, project: Project, prs: list[dict], listed: bool) -> int:
    """Inserts or updates each pull request for this project, and fills the author of its analyses that have none
    (rows from "Analyse now" before T-096). Returns how many were written. The caller commits."""
    written = 0
    stamp = now()
    for pr in prs:
        facts = facts_of(pr)
        if not facts:
            continue
        mine = select(PullRequest).where(PullRequest.project_id == project.id, PullRequest.number == facts["number"])
        row = db.scalar(mine)
        if row is None:
            try:
                with db.begin_nested():  # a savepoint, so losing the race below undoes only this insert
                    db.add(PullRequest(project_id=project.id, repo=project.repo, **facts))
            except IntegrityError:
                pass  # another writer saved this pull request first: update its row instead
            row = db.scalar(mine)
        if row is None:
            continue
        for key, value in facts.items():
            if value is None and key in ("head_ref", "base_ref"):
                continue  # a payload without its branches never erases the saved ones
            setattr(row, key, value)
        if listed:
            row.listed_at = stamp
        if facts["author"]:
            db.execute(update(RiskAssessment)
                       .where(RiskAssessment.project_id == project.id, RiskAssessment.pr_number == facts["number"],
                              RiskAssessment.author.is_(None))
                       .values(author=facts["author"]))
        written += 1
    db.flush()
    return written


def list_pulls(repo: str, token: str | None) -> list[dict]:
    """GitHub's pull requests of the repository, most recently updated first, up to MAX_PAGES pages.
    Raises httpx.HTTPStatusError when GitHub refuses."""
    out: list[dict] = []
    with httpx.Client(timeout=20, headers=_headers(token)) as c:
        for page in range(1, MAX_PAGES + 1):
            r = c.get(f"{API}/repos/{repo}/pulls",
                      params={"state": "all", "sort": "updated", "direction": "desc", "per_page": 100, "page": page})
            r.raise_for_status()
            batch = r.json()
            out += [p for p in batch if isinstance(p, dict)]
            if len(batch) < 100:
                break
    return out


def listed_at(db: Session, project: Project) -> datetime | None:
    last = db.scalar(select(func.max(PullRequest.listed_at)).where(PullRequest.project_id == project.id))
    return last.replace(tzinfo=last.tzinfo or now().tzinfo) if last else None  # SQLite drops the time zone


def is_stale(db: Session, project: Project) -> bool:
    last = listed_at(db, project)
    return last is None or now() - last > LIST_TTL


def sync(db: Session, project: Project, token: str | None) -> int:
    """Reads GitHub's list and saves it. Commits."""
    written = save(db, project, list_pulls(project.repo, token), listed=True)
    db.commit()
    return written


def branches(db: Session, project: Project) -> list[dict]:
    """T-099: every branch a saved pull request comes from or goes into, with how many pull requests touch it,
    busiest first. Always for the whole repository, so the screen can offer every branch while one is selected."""
    count: dict[str, int] = {}
    for head, base in db.execute(select(PullRequest.head_ref, PullRequest.base_ref).where(PullRequest.project_id == project.id)):
        for name in {head, base}:
            if name:
                count[name] = count.get(name, 0) + 1
    return [{"name": n, "pulls": c} for n, c in sorted(count.items(), key=lambda kv: (-kv[1], kv[0]))]


def rows_json(db: Session, project: Project, branch: str | None = None) -> dict:
    """The saved pull requests, newest activity first, each with its latest analysis if it has one. With `branch`,
    only the pull requests coming from or going into that branch (T-099)."""
    query = select(PullRequest).where(PullRequest.project_id == project.id)
    if branch:
        query = query.where(or_(PullRequest.head_ref == branch, PullRequest.base_ref == branch))
    prs = db.scalars(query.order_by(PullRequest.gh_updated_at.desc(), PullRequest.number.desc())).all()
    latest: dict[int, RiskAssessment] = {}
    for a in db.scalars(select(RiskAssessment).where(RiskAssessment.project_id == project.id, RiskAssessment.repo == project.repo)
                        .order_by(RiskAssessment.created_at.desc(), RiskAssessment.id.desc())):
        latest.setdefault(a.pr_number, a)
    return {
        "listed_at": _iso(listed_at(db, project)),
        "stale": is_stale(db, project),
        "branch": branch or None,
        "branches": branches(db, project),
        "items": [{
            "number": p.number, "title": p.title, "author": p.author, "state": p.state,
            "draft": p.draft, "url": p.html_url, "head_sha": p.head_sha, "head_ref": p.head_ref, "base_ref": p.base_ref, "created_at": _iso(p.gh_created_at),
            "updated_at": _iso(p.gh_updated_at),
            "analysis_id": latest[p.number].id if p.number in latest else None,
        } for p in prs],
    }
