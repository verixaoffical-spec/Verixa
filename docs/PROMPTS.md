# Prompt Registry

One entry per prompt. Change a prompt = bump the version and add a one-line reason. No model names in prompts.

## Template
### <agent>/<prompt-name> vX
- Purpose:
- Input schema:
- Output schema (enum / pydantic):
- Prompt file path:
- Eval result (accuracy, date):
- Changelog: vX date, reason

## Prompts
### analysis/risk-questions v1
- Purpose: 4 yes/no questions (auth, money, validation, data) about what a diff does; a yes majority of 3 may only raise the rule label (D-011)
- Input schema: PR title + diff summary (secrets already hidden), both marked as data
- Output schema: Answers {auth, money, validation, data: "yes"|"no"}, extra keys forbidden (agents/risk_questions.py)
- Prompt file path: agents/risk_questions.py (SYSTEM, user_prompt)
- Eval result: T-034 live checks 2026-11-14, removed admin check -> auth yes majority; typo fix -> no raise
- Changelog: v1 2026-11-14, first version (T-034)
- test/select-tests (TODO)
- test/classify-failure (TODO) : only for ambiguous cases after rules
- test/draft-test (TODO) : Playwright TS or Postman
- report/root-cause (TODO) : must cite log lines
- report/ticket-draft (TODO) : ticket schema
- manager/judgment-check (TODO) : "is this claim supported by evidence?"
