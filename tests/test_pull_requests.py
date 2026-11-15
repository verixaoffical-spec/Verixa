"""T-096: every pull request of the connected repository with its author, saved in pull_requests.

Only GitHub's pull request list is faked (backend.pull_requests.list_pulls). The routes, the staleness rule, the
upsert, the author backfill, the webhook save and the ownership checks are the real code.
"""
from datetime import timedelta
from unittest import mock

import httpx
from sqlalchemy import select, update

from backend import pull_requests
from backend.agent_db import PullRequest, RiskAssessment
from backend.analysis_service import analyse_pull_request
from backend.db import Project, SessionLocal, now

from .test_pr_views import REPO, SHA, PrViewsTest


def gh_pull(number: int, author: str, state="open", merged=False, updated="2026-11-10T00:00:00Z", **extra) -> dict:
    return {"number": number, "title": f"PR {number}", "user": {"login": author},
            "state": state, "merged_at": "2026-11-09T00:00:00Z" if merged else None, "draft": False,
            "html_url": f"https://github.com/{REPO}/pull/{number}", "head": {"sha": f"{number:040x}"},
            "created_at": "2026-11-01T00:00:00Z", "updated_at": updated, **extra}


LIST = [gh_pull(9, "grace", updated="2026-11-12T00:00:00Z"), gh_pull(8, "bob", state="closed", merged=True),
        gh_pull(7, "ada", updated="2026-11-11T00:00:00Z")]


class PullRequestsTest(PrViewsTest):
    def setUp(self):
        super().setUp()
        from backend.analysis_api import forced_lists
        forced_lists._fails.clear()  # the refresh limit is per server, so each test starts unthrottled

    def fake_list(self, prs=LIST, status=None):
        def list_pulls(repo, token=None):
            if status:
                raise httpx.HTTPStatusError("no", request=httpx.Request("GET", "https://api.github.com"), response=httpx.Response(status))
            self.assertEqual((repo, token), (REPO, "gh-token"))
            return prs
        fake = mock.patch("backend.pull_requests.list_pulls", side_effect=list_pulls).start()
        self.addCleanup(mock.patch.stopall)
        return fake

    def test_every_pull_request_is_listed_with_its_author_and_saved(self):
        rid = self.own_row()  # PR 7 was analysed by "Analyse now" before T-096, so it has no author
        fake = self.fake_list()
        first = self.client.get("/api/analysis/repo-pulls").json()
        self.assertEqual((first["items"], first["stale"]), ([], True))  # nothing saved yet, so the screen asks for a sync

        res = self.client.post("/api/analysis/repo-pulls/sync")
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertFalse(body["stale"])
        self.assertEqual([(p["number"], p["author"], p["state"]) for p in body["items"]],
                         [(9, "grace", "open"), (7, "ada", "open"), (8, "bob", "merged")])  # newest activity first
        self.assertEqual(next(p for p in body["items"] if p["number"] == 7)["analysis_id"], rid)
        with SessionLocal() as db:
            self.assertEqual(db.get(RiskAssessment, rid).author, "ada")  # the old analysis got its author too
            self.assertEqual(len(db.scalars(select(PullRequest)).all()), 3)

        # fresh: neither the page nor a plain sync reads GitHub again; a forced refresh does
        self.client.get("/api/analysis/repo-pulls")
        self.client.post("/api/analysis/repo-pulls/sync")
        self.assertEqual(fake.call_count, 1)
        self.client.post("/api/analysis/repo-pulls/sync?force=true")
        self.assertEqual(fake.call_count, 2)
        with SessionLocal() as db:
            self.assertEqual(len(db.scalars(select(PullRequest)).all()), 3)  # updated in place, never duplicated

        # stale after LIST_TTL: read again
        with SessionLocal() as db:
            db.execute(update(PullRequest).values(listed_at=now() - pull_requests.LIST_TTL - timedelta(seconds=1)))
            db.commit()
        self.assertTrue(self.client.get("/api/analysis/repo-pulls").json()["stale"])
        self.client.post("/api/analysis/repo-pulls/sync")
        self.assertEqual(fake.call_count, 3)

    def test_unsafe_links_are_not_saved(self):
        self.own_row()
        self.fake_list([gh_pull(5, "mallory", html_url="javascript:alert(1)")])
        item = self.client.post("/api/analysis/repo-pulls/sync").json()["items"][0]
        self.assertEqual((item["url"], item["author"]), (None, "mallory"))

    def test_two_writers_saving_the_same_pull_request_do_not_fail(self):
        """A webhook and a list read can insert the same row at once; the second one updates it instead of failing."""
        self.own_row()
        with SessionLocal() as db:
            project = db.scalar(select(Project))
            pull_requests.save(db, project, [gh_pull(3, "first")], listed=False)
            db.commit()
            real = db.scalar
            calls = {"n": 0}

            def first_lookup_misses(stmt, *a, **k):  # the race: this writer looked before the other one inserted
                calls["n"] += 1
                return None if calls["n"] == 1 else real(stmt, *a, **k)
            with mock.patch.object(db, "scalar", side_effect=first_lookup_misses):
                self.assertEqual(pull_requests.save(db, project, [gh_pull(3, "second")], listed=True), 1)
            db.commit()
            rows = db.scalars(select(PullRequest)).all()
            self.assertEqual([(r.number, r.author) for r in rows], [(3, "second")])

    def test_negative_forced_refreshes_are_rate_limited(self):
        self.own_row()
        fake = self.fake_list()
        codes = [self.client.post("/api/analysis/repo-pulls/sync?force=true").status_code for _ in range(8)]
        self.assertEqual(codes, [200] * 6 + [429] * 2)
        self.assertEqual(fake.call_count, 6)

    def test_a_webhook_delivery_saves_its_pull_request_and_author(self):
        self.own_row()
        payload = {"action": "opened", "number": 12, "repository": {"full_name": REPO},
                   "pull_request": {"title": "New one", "head": {"sha": SHA}, "user": {"login": "webhook-dev"},
                                    "html_url": f"https://github.com/{REPO}/pull/12", "state": "open"}}
        with mock.patch("backend.analysis_service._score_one", new=mock.AsyncMock()):
            import asyncio
            asyncio.run(analyse_pull_request(payload, "d-1"))
        items = self.client.get("/api/analysis/repo-pulls").json()["items"]
        self.assertEqual([(p["number"], p["author"], p["title"]) for p in items], [(12, "webhook-dev", "New one")])

    def test_negative_github_refusing_is_a_clear_502_and_nothing_is_saved(self):
        self.own_row()
        self.fake_list(status=403)
        res = self.client.post("/api/analysis/repo-pulls/sync")
        self.assertEqual(res.status_code, 502)
        self.assertIn("GitHub refused to list the pull requests (403)", res.json()["detail"])
        self.assertEqual(self.client.get("/api/analysis/repo-pulls").json()["items"], [])

    def test_negative_another_account_never_sees_them_and_github_is_not_asked(self):
        self.own_row()
        fake = self.fake_list()
        self.client.post("/api/analysis/repo-pulls/sync")
        other = self.new_client()
        self.linked_user("eve@example.com", client=other)
        self.assertEqual(other.get("/api/analysis/repo-pulls").json()["items"], [])
        self.assertEqual(other.post("/api/analysis/repo-pulls/sync").status_code, 409)  # no project of her own
        self.assertEqual(fake.call_count, 1)
        self.assertEqual(self.new_client().get("/api/analysis/repo-pulls").status_code, 401)

    def test_negative_a_post_from_another_site_is_refused(self):
        self.own_row()
        self.fake_list()
        res = self.client.post("/api/analysis/repo-pulls/sync", headers={"Origin": "https://evil.example"})
        self.assertEqual(res.status_code, 403)

    def test_removing_the_project_removes_its_pull_requests(self):
        self.own_row()
        self.fake_list()
        self.client.post("/api/analysis/repo-pulls/sync")
        from backend.api import remove_project
        from backend.db import User
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == "ada@example.com"))
            remove_project(db, user)
            db.commit()
            self.assertEqual(db.scalars(select(PullRequest)).all(), [])


def load_tests(loader, tests, pattern):
    """Only this file's own tests: PullRequestsTest inherits PrViewsTest's helpers, not its tests (they run there)."""
    own = [n for n, v in vars(PullRequestsTest).items() if n.startswith("test_") and callable(v)]
    return loader.suiteClass(PullRequestsTest(n) for n in own)
