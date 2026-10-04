# Security and Privacy

## Secrets
- All keys in .env, never committed. .env.example lists names only.
- Claude Code is denied reading .env (see .claude/settings.json).
- Rotate any key that ever appears in a commit, log, or chat.

## Redaction (evidence/redaction.py)
Remove before any LLM call, storage in a ticket, or screenshot of logs:
API keys, bearer tokens, passwords, cookies, session IDs, JWTs, private keys, connection strings, emails and phone numbers where not needed.
Redaction needs tests with realistic fake secrets. Record `redacted=true` on evidence rows.

## LLM data handling
- Free tiers may train on inputs. Gemini free tier: sample/fake repos only.
- Send the minimum context (diff + needed log lines), not whole repos.

## Webhooks and auth
- Verify GitHub webhook signature on every request.
- Store OAuth tokens encrypted. Least-privilege scopes.
- Jira filing only after an approval row exists for gate 3.

## Execution safety
- Tests run on staging only. Refuse to run if STAGING_BASE_URL looks like production.
- Subprocesses (Newman, Playwright) have timeouts and no access to secrets beyond what the test needs.
- Uploaded spec files are untrusted code: run in an isolated working directory.
