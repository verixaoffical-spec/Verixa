"""T-034 Yes/no risk questions + majority vote of 3 (D-011: answers can only raise the rule label).

Asserts (offline):
  1. Every model answer must fit the strict yes/no schema: missing keys, extra keys and other words are rejected.
  2. The vote: 3/3 yes raises the label to the question's minimum; 2/3 raises it and is marked low confidence; 1/3 does
     not raise; "no" never lowers a label; fewer than 3 usable answers means no vote counts.
  3. Unusable answers are dropped (one broken answer of three -> no vote), and RISK_QUESTIONS=0 asks nothing.
Asserts (live, 6 small Groq calls, approved by the owner):
  4. A permission check removed from a neutrally named file gets a yes majority on "auth" and the label is raised.
  5. A docs-only change gets no yes majority and nothing is raised.
Negative cases are in 1-3 (rejected schemas, minority yes, all-no on a High label, broken answers).
"""
import asyncio, os, subprocess, sys

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


import backend  # noqa: E402,F401  (loads .env, as the app does)
from unittest import mock  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from agents import risk_questions as rq  # noqa: E402

NO = {"auth": "no", "money": "no", "validation": "no", "data": "no"}


def A(**yes) -> rq.Answers:
    return rq.Answers(**{**NO, **{k: "yes" for k in yes}})


# 1. schema
check("schema: a complete yes/no answer is accepted", rq.Answers.model_validate(NO) is not None)
for bad, label in (({**NO, "auth": "maybe"}, "another word"), ({k: v for k, v in NO.items() if k != "data"}, "a missing key"),
                   ({**NO, "extra": "yes"}, "an extra key")):
    try:
        rq.Answers.model_validate(bad)
        refused = False
    except ValidationError:
        refused = True
    check(f"negative: schema rejects {label}", refused)

# 2. the vote
low = {"risk_label": "Low", "risk_factors": ["size: 1 file"]}
r = rq.apply_votes(low, [A(auth=1)] * 3)
check("vote: 3/3 yes on auth raises Low to High", r["risk_label"] == "High" and any("3/3" in f and "raised" in f for f in r["risk_factors"]))
r = rq.apply_votes(low, [A(auth=1), A(auth=1), A()])
check("vote: 2/3 yes raises it and is marked low confidence", r["risk_label"] == "High" and any("low confidence" in f for f in r["risk_factors"]))
r = rq.apply_votes(low, [A(auth=1), A(), A()])
check("negative: 1/3 yes does not raise", r["risk_label"] == "Low")
r = rq.apply_votes(low, [A(validation=1)] * 3)
check("vote: a Medium question raises Low only to Medium", r["risk_label"] == "Medium")
high = {"risk_label": "High", "risk_factors": []}
check("negative: all-no answers never lower a High label", rq.apply_votes(high, [A()] * 3)["risk_label"] == "High")
r = rq.apply_votes(low, [A(auth=1)] * 2)
check("negative: with only 2 usable answers no vote counts", r["risk_label"] == "Low" and any("no vote counted" in f for f in r["risk_factors"]))
check("the rule facts are not modified in place", low == {"risk_label": "Low", "risk_factors": ["size: 1 file"]})

# 3. broken answers dropped; switch off
replies = iter([(NO, "m"), ({"auth": "perhaps"}, "m"), ({**NO, "auth": "yes"}, "m")])
with mock.patch.object(rq, "ask", side_effect=lambda *a, **k: next(replies)):  # an async function, so this is an AsyncMock
    got = asyncio.run(rq.ask_questions("t", "d"))
check("negative: a broken answer is dropped (3 asked, 2 usable)", len(got) == 2)
with mock.patch.dict(os.environ, {"RISK_QUESTIONS": "0"}), mock.patch.object(rq, "ask") as asked:
    check("RISK_QUESTIONS=0 asks nothing", asyncio.run(rq.ask_questions("t", "d")) == [] and asked.call_count == 0)

# asked once per commit: a Manager retry reuses the vote instead of asking 3 more times
from agents import analysis  # noqa: E402
st = {}
calls = []
async def fake_questions(t, d):
    calls.append(1)
    return [A(auth=1)] * 3
facts0 = {"head_sha": "a" * 40, "title": "t", "diff_summary": "d", "risk_label": "Low", "risk_factors": [], "has_code": True}
with mock.patch.object(analysis, "ask_questions", side_effect=fake_questions):
    for _ in range(3):  # three Manager attempts on the same commit
        if st.get("votes_sha") != facts0["head_sha"]:
            st["votes"] = asyncio.run(analysis.ask_questions("t", "d")); st["votes_sha"] = facts0["head_sha"]
src = open("agents/analysis.py", encoding="utf-8").read()
check("votes are cached per commit in the agent (no new vote on a Manager retry)",
      'st.get("votes_sha") != facts["head_sha"]' in src and len(calls) == 1, f"{len(calls)} votes for 3 attempts")

# 4./5. live
risky = ("src/views/report.ts (+3/-6)\n"
         "-export function showReport(req, res) {\n"
         "-  if (!req.session.user || !req.session.user.isAdmin) {\n"
         "-    return res.status(403).send('forbidden')\n"
         "-  }\n"
         "+export function showReport(req, res) {\n"
         "   return res.send(loadAllSalaries())")
answers = asyncio.run(rq.ask_questions("Tidy report view", risky))
yes = sum(a.auth == rq.YesNo.yes for a in answers)
check("live: 3 schema-valid answers for the permission-removal diff", len(answers) == 3, f"{len(answers)} usable")
check("live: majority says the removed admin check weakens auth", yes >= 2, f"{yes}/3 yes")
check("live: that vote raises a Low rule label to High", rq.apply_votes(low, answers)["risk_label"] == "High")
docs = "README.md (+1/-1)\n-Instal the app\n+Install the app"
answers = asyncio.run(rq.ask_questions("Fix typo", docs))
raised = rq.apply_votes(low, answers)
check("live: a docs-only typo fix raises nothing", len(answers) == 3 and raised["risk_label"] == "Low",
      f"{len(answers)} usable, label {raised['risk_label']}")

print(f"\n{'PASS' if not fails else 'FAIL'}: {len(fails)} failed" + (f" ({', '.join(fails)})" if fails else ""))
sys.exit(1 if fails else 0)
