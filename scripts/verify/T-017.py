"""T-017 Spike: ADK with Groq and OpenRouter models (LiteLLM).

Live calls, tiny prompts (the owner approved live calls). Keys come from .env and are never printed.
Asserts:
  1. An ADK LlmAgent on a Groq model (agents.models.adk_model -> LiteLlm) answers through the ADK Runner.
  2. The same on an OpenRouter model.
  3. The fallback chain (agents.llm.ask) skips a model that fails and answers with the next one, reporting
     which model answered, and returns parsed JSON.
Negative case: with no provider keys, every model is skipped and ask() raises "All models failed".
"""
import asyncio, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (".venv/Scripts/python.exe", ".venv/bin/python"):  # run.py uses the system python; the app needs .venv
    _venv = os.path.join(ROOT, _p)
    if os.path.exists(_venv) and os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(_venv):
        sys.exit(subprocess.run([_venv, os.path.abspath(__file__)]).returncode)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


import backend  # noqa: E402,F401  (loads .env into the environment, as the app does)
from unittest import mock  # noqa: E402
from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402
from agents import llm  # noqa: E402
from agents.models import adk_model  # noqa: E402

GROQ = llm.DEFAULT_CHAINS["analysis"][0]  # from the chain table, not hardcoded here
# The chains' OpenRouter models (qwen3-8b, deepseek-v4) were removed by OpenRouter in Oct 2026 and the
# replacement is Farheen's open choice (STATUS.md). The spike only proves ADK works with OpenRouter, so it uses a
# model that exists today; the app's chains are not changed by this check.
OPENROUTER = "openrouter/qwen/qwen3-14b"


async def adk_answer(model_name: str) -> str:
    agent = LlmAgent(name="pong", model=adk_model(model_name),
                     instruction="Reply with exactly one word: PONG. No punctuation, no other text.")
    service = InMemorySessionService()  # a spike: no need to keep these sessions
    session = await service.create_session(app_name="t017", user_id="check")
    text = ""
    async for event in Runner(agent=agent, app_name="t017", session_service=service).run_async(
            user_id="check", session_id=session.id, new_message=types.Content(role="user", parts=[types.Part(text="ping")])):
        for part in (event.content.parts if event.content and event.content.parts else []):
            text += part.text or ""
    return text


for label, name in (("Groq", GROQ), ("OpenRouter", OPENROUTER)):
    try:
        answer = asyncio.run(adk_answer(name))
        check(f"ADK LlmAgent on {label} ({name}) answers through the Runner", "PONG" in answer.upper(), repr(answer[:80]))
    except Exception as exc:
        check(f"ADK LlmAgent on {label} ({name}) answers through the Runner", False, f"{type(exc).__name__}: {str(exc)[:160]}")

# fallback: a model that cannot work first, the real one second
with mock.patch.dict(os.environ, {"ANALYSIS_MODELS": f"groq/verixa-no-such-model,{GROQ}"}):
    try:
        answer, used = asyncio.run(llm.ask("analysis", "Answer only with JSON.", 'Return {"ok": true}', as_json=True, timeout=45))
        check("fallback: a failing model is skipped and the next one answers", used == GROQ, f"answered by {used}")
        check("fallback: the answer is parsed JSON", answer == {"ok": True}, repr(answer))
    except Exception as exc:
        check("fallback: a failing model is skipped and the next one answers", False, f"{type(exc).__name__}: {str(exc)[:160]}")

# negative: no keys at all
with mock.patch.dict(os.environ, {"GROQ_API_KEY": "", "OPENROUTER_API_KEY": "", "GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
    try:
        asyncio.run(llm.ask("analysis", "x", "y"))
        raised = ""
    except RuntimeError as exc:
        raised = str(exc)
check("negative: with no keys every model is skipped and ask() raises",
      raised.startswith("All models failed") and raised.count("no API key") == len(llm.chain("analysis")), raised[:160])

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
