"""T-094: analysis artifacts are saved once and served from the database (D-013).

Only GitHub's answers are faked. The routes, the snapshot table, the step writer thread and the index are real.
"""
from unittest import mock

from sqlalchemy import func, select

from agents.analysis import Bounded
from backend import model_calls
from backend.agent_db import AgentStep, PrFileSnapshot, RiskAssessment
from backend.db import SessionLocal

from .test_pr_views import FILES, REPO, SHA, SOURCES, PrViewsTest


class PersistTest(PrViewsTest):
    def fetch_counter(self, head=SHA):
        fetch = mock.patch("backend.pr_files.fetch_pr", return_value=({"head": {"sha": head}}, FILES)).start()
        mock.patch("backend.pr_files._read", side_effect=lambda repo, path, sha, token: SOURCES.get(path, "")).start()
        self.addCleanup(mock.patch.stopall)
        return fetch

    def snapshots(self) -> int:
        with SessionLocal() as db:
            return db.scalar(select(func.count()).select_from(PrFileSnapshot))

    def test_files_are_read_from_github_once_then_from_the_database(self):
        rid = self.own_row()
        fetch = self.fetch_counter()
        first = self.client.get(f"/api/analysis/pull-requests/{rid}/files").json()
        second = self.client.get(f"/api/analysis/pull-requests/{rid}/files").json()
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual((first["cached"], second["cached"]), (False, True))
        self.assertEqual({**first, "cached": True}, second)
        self.assertEqual(self.snapshots(), 1)

    def test_negative_a_pr_that_moved_on_is_not_saved(self):
        rid = self.own_row()
        fetch = self.fetch_counter(head="b" * 40)
        for _ in range(2):
            self.assertFalse(self.client.get(f"/api/analysis/pull-requests/{rid}/files").json()["cached"])
        self.assertEqual((fetch.call_count, self.snapshots()), (2, 0))

    def test_negative_a_saved_snapshot_is_still_private(self):
        rid = self.own_row()
        self.fetch_counter()
        self.client.get(f"/api/analysis/pull-requests/{rid}/files")
        other = self.new_client()
        self.linked_user("eve@example.com", client=other)
        self.assertEqual(other.get(f"/api/analysis/pull-requests/{rid}/files").status_code, 404)

    def test_run_steps_are_saved_and_served_from_the_database(self):
        rid = self.own_row()
        pr = f"{REPO}#7"
        for i, (event, run, extra) in enumerate([("service.delivery", None, {"action": "opened"}), ("run.start", "r1", {}),
                                                 ("rules.scored", "r1", {"risk_label": "High", "score": 7}),
                                                 ("analysis.cache_used", "r1", {}),  # not shown in the live view, not saved
                                                 ("service.saved", None, {"state": "scored"})]):
            model_calls.record_step({"at": f"2026-11-15T10:00:0{i}+00:00", "run_id": run, "pr_id": pr, "event": event, **extra})
        self.assertTrue(model_calls.flush())
        with SessionLocal() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(AgentStep)), 4)
        with mock.patch("backend.analysis_api.pr_log") as from_file:
            runs = self.client.get(f"/api/analysis/pull-requests/{rid}/log").json()["runs"]
        from_file.assert_not_called()  # the database answered; the trace file was not read
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["run_id"], "r1")
        self.assertEqual([m["stage"] for m in runs[0]["messages"]], ["received", "received", "rules", "saved"])
        self.assertEqual(runs[0]["messages"][2]["text"], "Risk rules scored it High (7 points)")
        self.assertTrue(runs[0]["messages"][-1]["done"])

    def test_the_log_keeps_the_newest_steps(self):
        rid = self.own_row()
        pr = f"{REPO}#7"
        for run in ("r1", "r2", "r3"):
            model_calls.record_step({"at": f"2026-11-15T1{run[1]}:00:00+00:00", "run_id": run, "pr_id": pr, "event": "run.start"})
        self.assertTrue(model_calls.flush())
        with mock.patch("backend.analysis_api.LOG_STEPS", 2):
            runs = self.client.get(f"/api/analysis/pull-requests/{rid}/log").json()["runs"]
        self.assertEqual([r["run_id"] for r in runs], ["r3", "r2"])  # the oldest, r1, is past the limit

    def test_a_snapshot_from_older_rules_is_read_again_and_replaced(self):
        rid = self.own_row()
        with SessionLocal() as db:
            db.add(PrFileSnapshot(assessment_id=rid, head_sha=SHA, data='{"version": 0, "files": []}'))
            db.commit()
        fetch = self.fetch_counter()
        first = self.client.get(f"/api/analysis/pull-requests/{rid}/files").json()
        second = self.client.get(f"/api/analysis/pull-requests/{rid}/files").json()
        self.assertEqual((fetch.call_count, first["cached"], second["cached"], len(second["files"])), (1, False, True, 5))
        self.assertEqual(self.snapshots(), 1)

    def test_indexes_and_bounded_cache(self):
        # The models declare both indexes (create_all and migration 0003 build them; the Neon check is in scripts/verify/T-094.py)
        self.assertIn(("project_id", "repo", "created_at"), {tuple(c.name for c in i.columns) for i in RiskAssessment.__table__.indexes if i.name == "ix_risk_feed"})
        self.assertIn(("repo", "pr_number", "at"), {tuple(c.name for c in i.columns) for i in AgentStep.__table__.indexes if i.name == "ix_agent_steps_pr"})
        cache = Bounded(3)
        for i in range(10):
            cache[i] = {"token": "x"}
        cache.setdefault(99, {})
        self.assertEqual(list(cache), [8, 9, 99])


def load_tests(loader, tests, pattern):
    """Only this file's own tests: PersistTest inherits PrViewsTest's helpers, not its tests (they run there)."""
    own = [n for n, v in vars(PersistTest).items() if n.startswith("test_") and callable(v)]
    return loader.suiteClass(PersistTest(n) for n in own)
