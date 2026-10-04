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
