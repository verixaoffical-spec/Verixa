# Project Overview

## Goal
Automate the path from "PR opened" to "ticket filed" with a supervised multi-agent system. A human controls the consequential steps. Also take the tester's existing Playwright specs and Postman collection and draft tests for coverage gaps.

## Problem
Testers jump between risk review, test runner, trace/log viewer, test tracker and Jira. Nothing carries context between them, so info is retyped. Verixa sits on top of the existing tools and chains them.

## Target users
Developers and testers in teams that review PRs on GitHub and track defects in Jira.

## FYP-I scope (in) : 7 deliverables
1. Connect GitHub repo + Jira project with one login, auto webhook setup
2. Upload Playwright (TS) specs and Postman collection into a Test Library, with live preview
3. Rule-based PR risk scoring (Low / Medium / High)
4. One-click run of relevant Playwright + Newman tests on staging
5. Draft new tests for coverage gaps
6. Results view with screenshots, traces, console and network logs
7. Review failure, approve, auto-file Jira ticket with evidence

## FYP-II (deferred, not dropped)
QA Memory (pgvector), Suggest a Fix, Regression Comparison, Cross-PR Risk Trend Reporting.

## Out of scope for the full year
Autonomous exploratory testing, security/load testing, mobile testing, production monitoring, auto-merging fixes.

## Assumptions
- Tests run on staging/dev, never production.
- Staging deployment happens outside Verixa.
- Tests already exist as TypeScript Playwright specs or a Postman collection.
- Tester manually approves running tests and filing tickets.

## Success criteria for FYP-I demo
- A PR opened on the test repo shows a risk label within seconds.
- Run Now executes UI + API tests and shows results with evidence.
- A failure becomes a reviewed Jira ticket with evidence attached.
- An undeployed feature is shown as deployment pending, not failed.
- Secrets never appear in a ticket.

## Versions
v1.0 = FYP-1 complete (the seven deliverables above, all verified). v2.0 = FYP-2 complete. See VERSIONS.md.

## Schedule
FYP-I weeks 1-16, FYP-II weeks 17-32. Task-level plan is in BACKLOG.md.
