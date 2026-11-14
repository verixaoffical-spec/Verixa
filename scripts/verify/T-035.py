"""T-035 Manager Agent: validation, retry cap, escalation.

The real AnalysisManager runs through the real ADK Runner; its worker is scripted (no model) so each case is exact.
Asserts:
  1. A good answer on the first attempt is approved after 1 attempt, with the rule label.
  2. A bad answer, then a good one: approved after 2 attempts, and the second attempt received the first attempt's
     problems as feedback.
  3. Bad answers every time: stops at the cap of 3 (D-005) and hands the PR to a human (needs_human_review) with the
     reasons.
  4. A PR that cannot be read is not retried pointlessly: 1 attempt, then a human.
  5. validate() rejects each kind of bad output: not JSON, too-short reasoning, reasoning that contradicts the label,
     test areas not about the change, "safe / no testing needed" dismissals, an over-long concern.
  6. The Manager's existing tests pass (matching, trace, secrets on retry, live status).
Negative cases are 2-5.
"""
import asyncio, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in (".venv/Scripts/python.exe", ".venv/bin/python"):  # run.py uses the system python; the app needs .venv
    _venv = os.path.join(ROOT, _p)
    if os.path.exists(_venv) and os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(_venv):
        sys.exit(subprocess.run([_venv, os.path.abspath(__file__)]).returncode)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.update({"AGENT_TRACE_CONSOLE": "0"})
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(("ok   " if ok else "FAIL ") + name + (f" - {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


# 6. existing tests, in their own process (SQLite test database)
r = subprocess.run([sys.executable, "-m", "unittest", "tests.test_manager_matching", "tests.test_agent_trace",
                    "tests.test_agent_secrets", "tests.test_live"], capture_output=True, text=True, timeout=600)
check("the Manager's existing tests pass", r.returncode == 0 and (r.stderr or "").strip().endswith("OK"),
      " | ".join((r.stderr or "").strip().splitlines()[-3:]))

from google.adk.agents import BaseAgent  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402
from agents import manager  # noqa: E402
from agents.analysis import ANALYSES  # noqa: E402
from agents.events import text_event  # noqa: E402

DIFF = "src/cart/total.ts (+12/-2)\n+export function cartTotal(items) {\n+  return round(items.reduce(sum, 0))\n+}"
FACTS = {"risk_label": "Medium", "score": 5, "risk_factors": ["size: 1 file"], "diff_summary": DIFF, "has_code": True,
         "head_sha": "a" * 40, "title": "Round cart totals"}
GOOD = json.dumps({"reasoning": "The change rewrites cartTotal in src/cart/total.ts and adds rounding to the sum of items, "
                                "so totals shown at checkout can move by a cent.",
                   "suggested_test_areas": ["cartTotal rounding on many items", "checkout total matches cart total"],
                   "concern": ""})
BAD = json.dumps({"reasoning": "ok", "suggested_test_areas": ["x"]})


class Scripted(BaseAgent):
    """Stands in for the Analysis Agent: one scripted answer per attempt, and it remembers the feedback it got."""
    answers: list
    seen_feedback: list
    unreadable: bool = False

    async def _run_async_impl(self, ctx):
        pr_id = ctx.user_content.parts[0].text.removeprefix("Analyze ").strip()
        st = ANALYSES[pr_id]
        self.seen_feedback.append(st.get("feedback"))
        if self.unreadable:
            st["error"] = "could not read the pull request"
        else:
            st.update(facts=FACTS, raw=self.answers[min(len(self.seen_feedback), len(self.answers)) - 1], model="scripted",
                      error=None)
        yield text_event(self.name, "answered")


def run(worker: Scripted, pr: str) -> dict:
    mgr = manager.AnalysisManager(name="manager_agent", worker=worker, sub_agents=[worker])

    async def go():
        svc = InMemorySessionService()
        s = await svc.create_session(app_name="t035", user_id="check")
        async for _ in Runner(agent=mgr, app_name="t035", session_service=svc).run_async(
                user_id="check", session_id=s.id, new_message=types.Content(role="user", parts=[types.Part(text=f"Analyze {pr}")])):
            pass
        return ANALYSES[pr]["result"]
    return asyncio.run(go())


res = run(Scripted(name="w1", answers=[GOOD], seen_feedback=[]), "o/r#1")
check("good first answer: approved after 1 attempt, rule label kept",
      res["status"] == "approved" and res["attempts"] == 1 and res["analysis"]["risk_label"] == "Medium", str(res)[:160])

w = Scripted(name="w2", answers=[BAD, GOOD], seen_feedback=[])
res = run(w, "o/r#2")
check("bad then good: approved after 2 attempts", res["status"] == "approved" and res["attempts"] == 2, str(res)[:160])
check("the retry received the first attempt's problems as feedback", w.seen_feedback[0] is None and "reasoning" in (w.seen_feedback[1] or ""),
      str(w.seen_feedback))

w = Scripted(name="w3", answers=[BAD], seen_feedback=[])
res = run(w, "o/r#3")
check("bad every time: stops at 3 attempts (D-005)", res["attempts"] == 3 and len(w.seen_feedback) == 3, f"{res['attempts']} / {len(w.seen_feedback)}")
check("then hands it to a human with the reasons", res["status"] == "needs_human_review" and bool(res["errors"]), str(res)[:160])

w = Scripted(name="w4", answers=[GOOD], seen_feedback=[], unreadable=True)
res = run(w, "o/r#4")
check("unreadable PR: no pointless retries, 1 attempt then a human", res["attempts"] == 1 and res["status"] == "needs_human_review",
      str(res)[:160])

# 5. validate() rejects each kind of bad output
def rejects(raw: str, label: str = "Medium") -> list[str]:
    ANALYSES["o/r#9"] = {"facts": {**FACTS, "risk_label": label}, "raw": raw, "model": "m"}
    return manager.validate("o/r#9")[1]


good = json.loads(GOOD)
cases = [("not JSON", "this is not json", "Medium"),
         ("too-short reasoning", json.dumps({**good, "reasoning": "fine"}), "Medium"),
         ("reasoning that contradicts a High label", json.dumps({**good, "reasoning": "This is a low risk change to cartTotal in "
                                                                "src/cart/total.ts with rounding."}), "High"),
         ("test areas not about the change", json.dumps({**good, "suggested_test_areas": ["login page", "password reset"]}), "Medium"),
         ("a 'safe, no testing needed' dismissal", json.dumps({**good, "reasoning": good["reasoning"] + " It is safe and needs no testing."}), "Medium"),
         ("an over-long concern", json.dumps({**good, "concern": "x " * 300}), "Medium")]
check("validate accepts the good answer", rejects(GOOD) == [])
errs = rejects(json.dumps({"reasoning": ["not", "text"], "suggested_test_areas": "one string"}))
check("negative: an answer that does not fit the pydantic schema is rejected, naming the fields",
      bool(errs) and "schema" in errs[0] and "reasoning" in errs[0] and "suggested_test_areas" in errs[0], str(errs))

# feedback really reaches the prompt the real Analysis Agent sends to the model
from agents.analysis import _instruction  # noqa: E402
FULL = {**FACTS, "pr_id": "o/r#10", "module": "cart", "modules_touched": ["cart"], "files_changed": 1, "lines_changed": 14,
        "past_defects_in_module": 0, "sensitivity": "none", "base_label": "Medium",
        "scoring_basis": "size + defect history + sensitive areas, with minimum labels"}
ANALYSES["o/r#10"] = {"facts": FULL, "feedback": "reasoning must be 2-3 sentences."}
ctx = type("Ctx", (), {"user_content": types.Content(role="user", parts=[types.Part(text="Analyze o/r#10")])})()
check("the Manager's feedback is written into the real prompt on a retry", "reasoning must be 2-3 sentences." in _instruction(ctx))
for label, raw, risk in cases:
    errs = rejects(raw, risk)
    check(f"negative: validate rejects {label}", bool(errs), "accepted")

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
