# Versions

**VERSION 1.0 = FYP-1 COMPLETE.** Everything planned for FYP-1 is DONE and verified. FYP-2 work (T-100 onward) is locked until then.
**VERSION 2.0 = FYP-2 COMPLETE.**

Versions are computed from BACKLOG.md + VERIFICATION.md by `.claude/hooks/version_status.py`. Do not claim a version by hand.
Check any time: `python3 .claude/hooks/version_status.py` or /version.

## Scheme
| Version | Meaning | Tasks |
|---|---|---|
| v0.1 | Environment: DB, API scaffold, CI, ADK skeleton, staging app | T-010..T-019 |
| v0.2 | D1: connect GitHub + Jira, webhook, upload, Test Library, LLM router | T-020..T-026 |
| v0.3 | D2: risk scoring, Manager Agent | T-030..T-037 |
| v0.4 | D3: one-click test run, failure classification, gap drafting | T-040..T-051 |
| v0.5 | D4: evidence collection and results view | T-060..T-064 |
| v0.6 | D5: Report Agent, redaction, Jira filing | T-070..T-075 |
| v0.9 | Integration testing and demo | T-080..T-082 |
| **v1.0** | **FYP-1 COMPLETE**: every task from T-001 to T-092 DONE and verified (T-093 is recurring, not counted) | |
| v2.0 | FYP-2 COMPLETE | T-100..T-140 |

## Release record (fill in when reached, git tag the commit)
| Version | Date reached | Git tag | Demoed to | Notes |
|---|---|---|---|---|
| v0.1 | | | | |
| v0.2 | | | | |
| v0.3 | | | | |
| v0.4 | | | | |
| v0.5 | | | | |
| v0.6 | | | | |
| v0.9 | | | | |
| **v1.0 (FYP-1)** | | v1.0-fyp1 | | |
| v2.0 (FYP-2) | | v2.0-fyp2 | | |

## When v1.0 is reached
1. Claude says it aloud: **FYP-1 IS COMPLETED. NOW FYP-2.**
2. Tag: `git tag -a v1.0-fyp1 -m "FYP-1 complete" && git push --tags`
3. Create branch `release/fyp1` from that commit and keep it working for the FYP-1 demo and thesis.
4. Record date and demo notes in the table above.
5. Review RISKS.md and DECISIONS.md, then start T-100 on `main`.
6. FYP-2 work must not break the v1.0 behaviour. Keep its verification scripts passing.
