# Model Plan (NOT FINAL)

Models are undecided. This is Farheen's starting guess, to be tested.

## Rules
- Names live in backend/llm/config.yaml. Never hardcode.
- Agents call the router. Router walks the priority list on failure or quota error and logs to model_calls.
- Run 20-30 cases per agent, then reorder from results. Record in TESTING.md.
- Before building, check Groq and OpenRouter dashboards for current free limits and that each model is still free.

## Priority (move right only if a model fails tests or free access disappears)
| Agent / task | P1 | P2 | P3 | Fallback | Safety check in code |
|---|---|---|---|---|---|
| Analysis: risk label | GPT OSS 20B (Groq) | GPT OSS 120B (Groq) | Qwen3 8B (OpenRouter) | Gemini Flash, sample repos only | Enum schema, majority vote of 3, flag low confidence |
| Test: selection + failure classification | GPT OSS 20B (Groq) | Qwen3 8B (OpenRouter) | GPT OSS 120B (Groq) | Gemini Flash, sample repos only | Rule check first, then enum schema |
| Test: drafting new tests | Qwen3 Coder (OpenRouter/Fireworks) | GPT OSS 120B (Groq) | DeepSeek V4 (OpenRouter) | Gemini Flash, sample repos only | TS compile, one run on staging |
| Report: root cause + ticket | GPT OSS 120B (Groq) | DeepSeek V4 (OpenRouter) | GLM 5.2 (OpenRouter) | Gemini Flash, sample repos only | Ticket schema, claims cite log lines, secrets removed |
| Manager: validation | Plain code | none | none | none | Retry cap, escalate |
| Manager: judgment check | GPT OSS 20B (Groq) | Qwen3 8B (OpenRouter) | GPT OSS 120B (Groq) | Gemini Flash, sample repos only | Run twice, disagreement = human review |

## Notes
- Gemini Flash is last: free tier may train on inputs. Sample or fake repos only.
- Later candidates: Kimi K2.6, Qwen3.7, MiniMax M3, Gemma 4 once free access is stable.
- MISMATCH: proposal 5.2 says Gemini primary, Groq fallback. This table reverses it. Fix before submission (task T-091).
- ADK is Gemini-first. Non-Gemini models need LiteLLM or a wrapper. Spike in T-017.
- Never send real customer code to a model whose free tier trains on inputs.

## Final choice
Status: undecided. When decided, record in DECISIONS.md and update this file.

## Removed by providers
- 2026-11-14 (found in T-017): OpenRouter removed `qwen/qwen3-8b` and `deepseek/deepseek-v4`. They are still in
  backend/llm/config.yaml so the chain order stays visible; calls to them fail and the chain moves on. Farheen will
  pick replacements (no OpenRouter option is free now; see STATUS.md Known issues).
