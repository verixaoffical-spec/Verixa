# Risks and Blockers

| ID | Risk | Likelihood | Impact | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|
| R1 | Free-tier rate limits or models lose free access | High | Med | Router fallback, check dashboards, keep priority list | Farheen | Open |
| R2 | ADK works poorly with non-Gemini models | Med | High | Spike in T-017 early | Farheen | Open |
| R3 | Uncapped agent retries | Low | Med | Retry cap + escalate | Farheen | Open |
| R4 | Two-person team, scope too big | Med | High | 7 deliverables only, FYP-II deferred | Both | Open |
| R5 | Jira official integration downtime | Low | Med | Community fallback behind interface | Arisha | Open |
| R6 | Evidence volume grows | Med | Low | Files on disk, paths in DB | Arisha | Open |
| R7 | Staging out of sync with PR | High | Med | deployment_pending check | Arisha | Open |
| R8 | Secrets leak into tickets or LLM calls | Low | High | Redaction + tests | Farheen | Open |
| R9 | Free tier trains on inputs | Med | Med | Gemini only for sample repos | Farheen | Open |
| R10 | Docs and status drift from reality | High | Med | /end-session every time, Friday review | Both | Open |
| R11 | Gate bypassed via Bash writes or a human editing hooks | Low | Med | CLAUDE.md rule, protected files, PR review, Friday review of VERIFICATION.md | Both | Open |
| R12 | Strict gate stalls one person while the other is late | Med | Med | /next-task picks unblocked work, finish upstream tasks early, flag delays Monday | Both | Open |

## Active blockers
(none)
