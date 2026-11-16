"""T-099: defect history apart from the run's status, and the source and target branch of every pull request.

GitHub is faked at its edges only (the list, the PR read, the defect lookups, CI); the routes, the saved rows, the
branch filter, the analysis rules and the live messages are the real code.
"""
import asyncio
from unittest import mock

from sqlalchemy import select

from agents import analysis
from backend.agent_db import PullRequest, RiskAssessment, defect_history, to_json
from backend.analysis_service import analyse_pull_request
from backend.db import SessionLocal
from backend.live import describe

from .test_pr_views import REPO, SHA
from .test_pull_requests import PullRequestsTest, gh_pull


def on(head: str, base: str) -> dict:
    return {"head": {"sha": SHA, "ref": head}, "base": {"ref": base}}


BRANCHED = [gh_pull(9, "grace", updated="2026-11-12T00:00:00Z", **on("feature/login", "main")),
            gh_pull(8, "bob", **on("fix/cart", "develop")),
            gh_pull(7, "ada", updated="2026-11-11T00:00:00Z", **on("feature/login", "develop"))]


class BranchesTest(PullRequestsTest):
    def test_branches_are_saved_and_each_pull_request_is_filtered_by_its_branches(self):
        rid = self.own_row()  # PR 7's analysis
        self.fake_list(BRANCHED)
        body = self.client.post("/api/analysis/repo-pulls/sync").json()
        self.assertEqual({p["number"]: (p["head_ref"], p["base_ref"]) for p in body["items"]},
                         {9: ("feature/login", "main"), 8: ("fix/cart", "develop"), 7: ("feature/login", "develop")})
        self.assertEqual(body["branches"], [{"name": "develop", "pulls": 2}, {"name": "feature/login", "pulls": 2},
                                            {"name": "fix/cart", "pulls": 1}, {"name": "main", "pulls": 1}])
        with SessionLocal() as db:  # stored in the database, not only in the answer
            self.assertEqual(db.scalar(select(PullRequest.base_ref).where(PullRequest.number == 8)), "develop")

        def numbers(branch):
            res = self.client.get("/api/analysis/repo-pulls", params={"branch": branch})
            self.assertEqual(res.status_code, 200, res.text)
            return res.json()

        source = numbers("feature/login")  # from the branch
        self.assertEqual(([p["number"] for p in source["items"]], source["branch"]), ([9, 7], "feature/login"))
        self.assertEqual(len(source["branches"]), 4)  # every branch is still offered while one is selected
        self.assertEqual([p["number"] for p in numbers("develop")["items"]], [7, 8])  # into the branch
        self.assertEqual([p["number"] for p in numbers("main")["items"]], [9])
        # each pull request stays with its own analysis, whichever branch it is listed under
        self.assertEqual([(p["number"], p["analysis_id"]) for p in numbers("develop")["items"]], [(7, rid), (8, None)])
        self.assertEqual(self.client.post("/api/analysis/repo-pulls/sync?branch=fix/cart").json()["items"][0]["number"], 8)
        self.assertEqual(numbers("")["branch"], None)
        self.assertEqual(len(numbers("")["items"]), 3)

    def test_a_webhook_delivery_saves_the_branches_of_its_pull_request(self):
        self.own_row()
        payload = {"action": "opened", "number": 12, "repository": {"full_name": REPO},
                   "pull_request": {"title": "New one", "user": {"login": "webhook-dev"}, "state": "open", **on("feature/pay", "main")}}
        with mock.patch("backend.analysis_service._score_one", new=mock.AsyncMock()):
            asyncio.run(analyse_pull_request(payload, "d-99"))
        items = self.client.get("/api/analysis/repo-pulls", params={"branch": "feature/pay"}).json()["items"]
        self.assertEqual([(p["number"], p["head_ref"], p["base_ref"]) for p in items], [(12, "feature/pay", "main")])
        # a later payload without branches keeps the saved ones
        bare = {**payload, "action": "edited", "pull_request": {"title": "Renamed", "user": {"login": "webhook-dev"}, "state": "open"}}
        with mock.patch("backend.analysis_service._score_one", new=mock.AsyncMock()):
            asyncio.run(analyse_pull_request(bare, "d-100"))
        with SessionLocal() as db:
            self.assertEqual(db.execute(select(PullRequest.head_ref, PullRequest.base_ref).where(PullRequest.number == 12)).one(),
                             ("feature/pay", "main"))

    def test_negative_an_unknown_branch_lists_nothing_and_another_account_sees_no_branch(self):
        self.own_row()
        self.fake_list(BRANCHED)
        self.client.post("/api/analysis/repo-pulls/sync")
        self.assertEqual(self.client.get("/api/analysis/repo-pulls", params={"branch": "nope"}).json()["items"], [])
        # a branch name is matched exactly, never as a pattern
        self.assertEqual(self.client.get("/api/analysis/repo-pulls", params={"branch": "%"}).json()["items"], [])
        self.assertEqual(self.client.get("/api/analysis/repo-pulls", params={"branch": "x" * 256}).status_code, 422)
        other = self.new_client()
        self.linked_user("eve@example.com", client=other)
        mine = other.get("/api/analysis/repo-pulls", params={"branch": "develop"}).json()
        self.assertEqual((mine["items"], mine["branches"]), ([], []))

    def test_defect_history_is_reported_apart_from_the_run_state(self):
        self.assertEqual(defect_history("queued", None), "pending")     # really waiting: the run has not finished
        self.assertEqual(defect_history("running", 2), "pending")       # a re-run's old count is not this run's
        self.assertEqual(defect_history("scored", 0), "none")           # no history is a result, not a wait
        self.assertEqual(defect_history("scored", 3), "found")
        self.assertEqual(defect_history("needs_human_review", 0), "none")
        self.assertEqual(defect_history("scored", None), "unknown")     # negative: a failed lookup is never "none"
        self.assertEqual(defect_history("failed", None), "unknown")
        rid = self.own_row()
        with SessionLocal() as db:
            row = db.get(RiskAssessment, rid)
            row.state, row.past_defects = "scored", 0
            self.assertEqual(to_json(row)["defect_history"], "none")
            row.state = "running"
            self.assertEqual(to_json(row)["defect_history"], "pending")


def fake_pr(files):
    pr = {"title": "t", "head": {"sha": SHA}, "base": {"sha": "b" * 40, "repo": {"id": 1}, "ref": "main"},
          "user": {"login": "ada"}, "changed_files": len(files)}
    return mock.patch.object(analysis, "fetch_pr", return_value=(pr, files))


def run_rules(files, lookups=0):
    events = []
    with fake_pr(files), mock.patch.object(analysis, "read_ci", return_value=None), \
            mock.patch.object(analysis, "count_fix_commits", return_value=lookups), \
            mock.patch.object(analysis, "count_defects", return_value=lookups), \
            mock.patch.object(analysis, "trace", side_effect=lambda e, pr, **f: events.append((e, f))):
        result = analysis.score_pr(f"{REPO}#5", refresh=True, token="t")
    return result, events


def changed(name, status="modified"):
    return {"filename": name, "status": status, "additions": 5, "deletions": 1, "patch": "+x"}


class HistoryStageTest(PullRequestsTest):
    def test_a_new_module_reports_no_defect_history_instead_of_leaving_the_stage_waiting(self):
        result, events = run_rules([changed("billing/new.py", "added"), changed("billing/more.py", "added")])
        names = [e for e, _ in events]
        self.assertIn("github.defects_none", names)
        self.assertNotIn("github.defects_read", names)       # nothing was looked up
        self.assertEqual(result["past_defects_in_module"], 0)  # saved as "none", which the screen shows as No defect history
        reason = dict(events)["github.defects_none"]["reason"]
        message = describe({"event": "github.defects_none", "pr_id": f"{REPO}#5", "reason": reason, "at": "2026-11-16T00:00:00Z"})
        self.assertEqual((message["stage"], message["level"]), ("history", "info"))  # the history stage completes, no warning
        self.assertIn("no defect history", message["text"])

    def test_a_root_change_also_reports_no_defect_history(self):
        _, events = run_rules([changed("README.txt")])
        self.assertEqual(dict(events)["github.defects_none"]["reason"], "root")

    def test_negative_a_module_with_history_is_looked_up_and_not_reported_as_none(self):
        result, events = run_rules([changed("payments/charge.py")], lookups=4)
        names = [e for e, _ in events]
        self.assertEqual(names.count("github.defects_read"), 2)
        self.assertNotIn("github.defects_none", names)
        self.assertEqual(result["past_defects_in_module"], 4)


def load_tests(loader, tests, pattern):
    """Only this file's own tests, not the ones inherited from PullRequestsTest (they run in their own file)."""
    suite = loader.suiteClass()
    for cls in (BranchesTest, HistoryStageTest):
        suite.addTests(cls(n) for n, v in vars(cls).items() if n.startswith("test_") and callable(v))
    return suite
