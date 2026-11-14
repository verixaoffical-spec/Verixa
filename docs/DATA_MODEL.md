# Data Model (draft, update when migrations change)

| Table | Key columns | Notes |
|---|---|---|
| users | id, github_id, jira_account_id | one login for both |
| projects | id, user_id, repo_full_name, jira_project_key, webhook_id | |
| test_files | id, project_id, kind(playwright/postman), path, parsed_ok | uploaded files |
| test_cases | id, test_file_id, name, module, source(uploaded/drafted), approved | Test Library |
| pull_requests | id, project_id, number, title, head_sha, files_changed, lines_changed | |
| risk_assessments | id, pr_id, label(low/med/high), score, basis(history/size), confidence, model_used | |
| module_defect_history | id, project_id, module, defect_count, last_defect_at | feeds risk |
| test_runs | id, pr_id, status, started_at, finished_at, triggered_by | one run object |
| test_results | id, run_id, test_case_id, status(pass/fail/deployment_pending), classification(real_bug/timeout/deployment_pending), retries | |
| evidence | id, result_id, kind(screenshot/trace/console/network), path, redacted | paths only |
| tickets | id, run_id, result_id, draft_json, status(draft/approved/filed), jira_key | |
| approvals | id, run_id, gate(run/tests/ticket), approved_by, at | audit of human gates |
| agent_runs | id, run_id, agent, attempt, output_valid, error | retries and escalations |
| model_calls | id, agent, model, provider, tokens, latency_ms, ok, at | quota tracking and evals |
| adk_sessions | managed by ADK | |
| memory_embeddings | id, ticket_id, embedding vector | FYP-II |

## In the database now (T-012, 2026-11-14)
Created by Alembic migration `backend/migrations/versions/0001_baseline_the_eight_tables_from_mid.py` on the Neon
database in .env (D-009). These are mid's eight tables, unchanged; the planned tables above arrive with their tasks.

| Table | Owner (models) | Notes |
|---|---|---|
| users | backend/db.py | email or GitHub sign-in, tokens sealed, TOTP, session_version |
| recovery_codes | backend/db.py | 10 hashed 2FA recovery codes per user |
| password_resets | backend/db.py | hashed reset tokens |
| pending_signups | backend/db.py | email verification before an account exists |
| projects | backend/db.py | one repo + Jira project per user, webhook id |
| spec_files | backend/db.py | Test Library Playwright specs, revision for conflicts |
| collections | backend/db.py | Test Library Postman collection |
| risk_assessments | backend/agent_db.py | one row per (project, PR, head commit); folds in the pull_requests facts |

Schema changes go through a new Alembic revision (`.venv\Scripts\python.exe -m alembic revision --autogenerate -m "..."`,
then `alembic upgrade head`). The app's startup create_all only fills gaps and never alters a table.
Order matters on a new, empty database: run `alembic upgrade head` before the first app start. A database that the
app's create_all already built (no `alembic_version` row) is adopted with `alembic stamp head` instead.
