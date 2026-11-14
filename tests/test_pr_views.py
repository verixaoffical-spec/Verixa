"""T-038: the changed-files graph endpoint, the past-log endpoint and the live stage of each step.

Only the GitHub reads are faked (fetch_pr and the file-content read); the routes, the rules, the import finder,
the ownership check and the trace-log reader are the real code.
"""
import json
import os
import tempfile
from unittest import mock

import httpx
from backend.agent_db import AgentBase, RiskAssessment, init_agent_db
from backend.db import Project, SessionLocal, engine
from backend.live import describe, stage_of
from backend.pr_files import file_risk, imports_of

from .test_crud import CrudTestCase

REPO = "ada/shop"
SHA = "a" * 40
FILES = [
    {"filename": "src/api/login.ts", "status": "modified", "additions": 30, "deletions": 4, "patch": "+import x"},
    {"filename": "src/auth/token.ts", "status": "added", "additions": 80, "deletions": 0, "patch": "+export const t = 1"},
    {"filename": "src/cart/total.ts", "status": "modified", "additions": 5, "deletions": 5, "patch": "+round()"},
    {"filename": "README.md", "status": "modified", "additions": 1, "deletions": 1, "patch": "+typo"},
    {"filename": "src/api/guard.ts", "status": "modified", "additions": 0, "deletions": 1,
     "patch": "-  if (!isAuthenticated(req)) return deny()"},
]
SOURCES = {"src/api/login.ts": "import { t } from '../auth/token'\nimport { total } from '../cart/total.js'\nimport React from 'react'",
           "src/cart/total.ts": "export const total = 1", "src/auth/token.ts": "", "src/api/guard.ts": ""}


class PrViewsTest(CrudTestCase):
    def setUp(self):
        AgentBase.metadata.drop_all(engine)
        super().setUp()
        init_agent_db()

    def own_row(self, email="ada@example.com", client=None, sha=SHA) -> int:
        uid = self.linked_user(email, client)
        with SessionLocal() as db:
            project = Project(user_id=uid, repo=REPO, jira_key="QA", jira_name="QA")
            db.add(project)
            db.flush()
            row = RiskAssessment(project_id=project.id, repo=REPO, pr_number=7, head_sha=sha, state="scored",
                                 risk_label="High", base_label="High", title="Login refresh")
            db.add(row)
            db.commit()
            return row.id

    def fake_github(self, head=SHA, status=None):
        def fetch(repo, number, token=None):
            if status:
                raise httpx.HTTPStatusError("no", request=httpx.Request("GET", "https://api.github.com"),
                                            response=httpx.Response(status))
            self.assertEqual((repo, number, token), (REPO, 7, "gh-token"))
            return {"head": {"sha": head}}, FILES
        mock.patch("backend.pr_files.fetch_pr", side_effect=fetch).start()
        mock.patch("backend.pr_files._read", side_effect=lambda repo, path, sha, token: SOURCES.get(path, "")).start()
        self.addCleanup(mock.patch.stopall)

    # ---- the files endpoint ----

    def test_files_have_a_risk_each_and_the_imports_between_them(self):
        rid = self.own_row()
        self.fake_github()
        res = self.client.get(f"/api/analysis/pull-requests/{rid}/files")
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        risk = {f["path"]: f["risk"] for f in body["files"]}
        self.assertEqual(risk, {"src/api/login.ts": "High", "src/auth/token.ts": "High", "src/cart/total.ts": "Medium",
                                "README.md": "Low", "src/api/guard.ts": "High"})
        self.assertEqual(body["edges"], [["src/api/login.ts", "src/auth/token.ts"], ["src/api/login.ts", "src/cart/total.ts"]])
        self.assertTrue(body["same_commit"])
        self.assertEqual((body["total_files"], body["shown_files"], body["scanned_for_imports"]), (5, 5, 4))
        guard = next(f for f in body["files"] if f["path"] == "src/api/guard.ts")
        self.assertIn("login or permission check", guard["why"])
        self.assertEqual(guard["folder"], "src/api")

    def test_newer_commits_are_reported(self):
        rid = self.own_row()
        self.fake_github(head="b" * 40)
        self.assertFalse(self.client.get(f"/api/analysis/pull-requests/{rid}/files").json()["same_commit"])

    def test_github_refusing_is_a_clear_502(self):
        rid = self.own_row()
        self.fake_github(status=404)
        res = self.client.get(f"/api/analysis/pull-requests/{rid}/files")
        self.assertEqual((res.status_code, res.json()["detail"]), (502, "GitHub has no such pull request any more"))

    def test_negative_another_accounts_row_is_404_and_github_is_never_asked(self):
        rid = self.own_row()
        other = self.new_client()
        self.linked_user("eve@example.com", client=other)
        fetch = mock.patch("backend.pr_files.fetch_pr").start()
        self.addCleanup(mock.patch.stopall)
        for path in ("files", "log"):
            self.assertEqual(other.get(f"/api/analysis/pull-requests/{rid}/{path}").status_code, 404)
        fetch.assert_not_called()
        anonymous = self.new_client()
        self.assertEqual(anonymous.get(f"/api/analysis/pull-requests/{rid}/files").status_code, 401)

    # ---- the past-log endpoint ----

    def test_log_groups_saved_runs_newest_first_for_this_pr_only(self):
        rid = self.own_row()
        lines = [
            {"at": "2026-11-14T10:00:00", "run_id": None, "pr_id": f"{REPO}#7", "event": "service.delivery", "action": "opened"},
            {"at": "2026-11-14T10:00:01", "run_id": "r1", "pr_id": f"{REPO}#7", "event": "run.start"},
            {"at": "2026-11-14T10:00:02", "run_id": "r1", "pr_id": f"{REPO}#7", "event": "rules.scored", "risk_label": "High", "score": 7},
            {"at": "2026-11-14T10:00:03", "run_id": None, "pr_id": f"{REPO}#7", "event": "service.saved", "state": "scored"},
            {"at": "2026-11-14T10:05:00", "run_id": "x9", "pr_id": f"{REPO}#8", "event": "run.start"},
            {"at": "2026-11-14T11:00:00", "run_id": None, "pr_id": f"{REPO}#7", "event": "service.delivery", "action": "synchronize"},
            {"at": "2026-11-14T11:00:01", "run_id": "r2", "pr_id": f"{REPO}#7", "event": "run.start"},
        ]
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "trace.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(json.dumps(l) for l in lines) + "\nnot json\n")
        with mock.patch.dict(os.environ, {"AGENT_TRACE_FILE": path}):
            runs = self.client.get(f"/api/analysis/pull-requests/{rid}/log").json()["runs"]
        self.assertEqual([r["run_id"] for r in runs], ["r2", "r1"])
        self.assertEqual([m["stage"] for m in runs[1]["messages"]], ["received", "received", "rules", "saved"])
        self.assertEqual(runs[1]["messages"][2]["text"], "Risk rules scored it High (7 points)")
        self.assertTrue(all(m["pr"] == 7 for r in runs for m in r["messages"]))

    def test_no_trace_file_is_an_empty_list(self):
        rid = self.own_row()
        with mock.patch.dict(os.environ, {"AGENT_TRACE_FILE": os.path.join(tempfile.mkdtemp(), "none.jsonl")}):
            self.assertEqual(self.client.get(f"/api/analysis/pull-requests/{rid}/log").json(), {"runs": []})

    # ---- rules, imports and stages (pure) ----

    def test_rules_imports_and_stages(self):
        self.assertEqual(file_risk({"filename": "tests/a.test.ts", "patch": "-it('works', () => {})"})[0], "Medium")
        self.assertEqual(file_risk({"filename": "docs/x.md", "patch": "+a"}), ("Low", "test or documentation file"))
        paths = {"app/models.py", "app/views.py", "app/__init__.py", "lib/util/index.ts", "lib/a.ts"}
        self.assertEqual(imports_of("app/views.py", "from .models import User\nimport os", paths), {"app/models.py"})
        self.assertEqual(imports_of("lib/a.ts", "export * from './util'", paths), {"lib/util/index.ts"})
        self.assertEqual(imports_of("lib/a.ts", "import x from 'lodash'", paths), set())
        self.assertEqual(imports_of("app/views.py", "from . import (\n    models,\n)\n", paths), {"app/__init__.py", "app/models.py"})

    def test_a_hostile_file_name_stays_inside_the_contents_url(self):
        from backend import pr_files
        seen = []
        with mock.patch("backend.pr_files.httpx.get", side_effect=lambda url, **kw: seen.append((url, kw["params"])) or httpx.Response(404)):
            pr_files._read(REPO, "a%2e%2e/x?ref=y#z.ts", SHA, "t")
        self.assertEqual(seen, [(f"https://api.github.com/repos/{REPO}/contents/a%252e%252e/x%3Fref%3Dy%23z.ts", {"ref": SHA})])
        expected = {"service.delivery": "received", "run.start": "received", "github.pr_read": "changes",
                    "github.defects_read": "history", "github.ci_read": "ci", "ci.updated": "ci", "rules.scored": "rules",
                    "analysis.model_answered": "model", "manager.decided": "manager", "service.saved": "saved",
                    "run.crashed": "saved", "service.failed": "saved"}
        self.assertEqual({e: stage_of(e) for e in expected}, expected)
        self.assertEqual(describe({"event": "rules.scored", "pr_id": f"{REPO}#7", "risk_label": "Low", "score": 1})["stage"], "rules")
