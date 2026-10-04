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
- analysis/risk-questions (TODO) : small yes/no questions that feed the rule score
- test/select-tests (TODO)
- test/classify-failure (TODO) : only for ambiguous cases after rules
- test/draft-test (TODO) : Playwright TS or Postman
- report/root-cause (TODO) : must cite log lines
- report/ticket-draft (TODO) : ticket schema
- manager/judgment-check (TODO) : "is this claim supported by evidence?"
