"""Model chains per task, read from backend/llm/config.yaml (T-026; model names live only there).
Each task tries its models in order and moves to the next on any failure
(no key, quota, bad JSON). Override a chain with env, e.g. DRAFT_MODELS=a,b,c"""
import json
import os
import re
import time
from pathlib import Path

import litellm
import yaml

from .trace import trace

CONFIG = Path(os.getenv("MODEL_CONFIG", Path(__file__).resolve().parent.parent / "backend" / "llm" / "config.yaml"))


def load_chains(path: Path = CONFIG) -> dict[str, list[str]]:
    """The chains from config.yaml. A missing or malformed file stops the import: running with no models is worse."""
    chains = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("chains")
    if not isinstance(chains, dict) or not all(isinstance(v, list) and v and all(isinstance(m, str) and "/" in m for m in v)
                                               for v in chains.values()):
        raise ValueError(f"{path}: 'chains' must map each task to a non-empty list of provider/model names")
    return chains


DEFAULT_CHAINS = load_chains()
KEYS = {"groq/": "GROQ_API_KEY", "openrouter/": "OPENROUTER_API_KEY", "gemini/": "GEMINI_API_KEY"}


def chain(task: str) -> list[str]:
    env = os.getenv(f"{task.upper()}_MODELS", "")
    return [m.strip() for m in env.split(",") if m.strip()] or DEFAULT_CHAINS[task]


def _has_key(model: str) -> bool:
    if model.startswith("gemini/") and not os.getenv("GEMINI_API_KEY") and os.getenv("GOOGLE_API_KEY"):
        os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]
    for prefix, key in KEYS.items():
        if model.startswith(prefix):
            return bool(os.getenv(key))
    return True


def parse_json(text: str) -> dict:
    text = (text or "").strip()
    return json.loads(text[text.find("{"): text.rfind("}") + 1])


def strip_code(text: str) -> str:
    text = (text or "").strip()
    m = re.search(r"```[a-zA-Z]*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


async def ask(task: str, system: str, user: str, as_json: bool = True, timeout: int = 45, temperature: float = 0):
    """Returns (answer, model_used). Models without a key are skipped instantly."""
    errors = []
    for model in chain(task):
        if not _has_key(model):
            errors.append(f"{model}: no API key")
            continue
        kwargs = {}
        if model.startswith("groq/") and "gpt-oss" in model:
            kwargs["extra_body"] = {"include_reasoning": False}
        started = time.perf_counter()
        try:
            resp = await litellm.acompletion(
                model=model, temperature=temperature, timeout=timeout,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                **kwargs,
            )
            text = resp.choices[0].message.content or ""
            answer = parse_json(text) if as_json else strip_code(text)
            usage = getattr(resp, "usage", None)
            trace("llm.model_answered", task=task, model=model, ms=round((time.perf_counter() - started) * 1000),
                  tokens=getattr(usage, "total_tokens", None))
            return answer, model
        except Exception as e:
            errors.append(f"{model}: {type(e).__name__}: {str(e)[:120]}")
            trace("llm.model_failed", task=task, model=model, ms=round((time.perf_counter() - started) * 1000),
                  error=f"{type(e).__name__}: {str(e)[:300]}")
    raise RuntimeError("All models failed: " + " | ".join(errors))
