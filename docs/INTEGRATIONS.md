# Integrations

| System | How | Owner | Notes |
|---|---|---|---|
| GitHub | Official integration + OAuth App, webhook for PR opened/updated | Arisha | verify webhook signature, rate limits |
| Jira / Confluence | Official Atlassian integration, community fallback kept in reserve | Arisha | hide behind interface so fallback can swap in |
| Playwright | Official Microsoft integration, accessibility snapshots | Arisha | TS specs only |
| Newman | CLI subprocess (no official integration) | Arisha | timeout + capture JSON report |
| LLM providers | Via llm/router.py: Groq, OpenRouter, Gemini | Farheen | see MODELS.md |
| PostgreSQL | pgvector extension | Farheen | docker compose for local |

## Per-integration checklist
- Credentials in .env, listed in .env.example
- Interface in backend/integrations/, mockable in tests
- Failure behaviour defined (retry, fallback, surface to dashboard)
- Rate limits noted here

## Rate limits and quotas
(fill in after checking dashboards: Gemini ~1500 req/day free per proposal, Groq and OpenRouter limits TBD)
- GitHub pull request list (T-096): up to 3 calls (100 pull requests each) per read, made only when the saved list is older than 5 minutes and the Pull Requests view is opened, or when someone presses Refresh from GitHub (at most 6 a minute per account). Webhook deliveries update the list without any call.
- GitHub contents API (T-038): opening the Dependency graph for one PR makes up to about 71 GitHub calls (1 PR read, up to 30 file-list pages, up to 40 file reads to find imports). Since T-094 it is read once per analysed commit and saved; since T-096 the browser tab keeps it too.
