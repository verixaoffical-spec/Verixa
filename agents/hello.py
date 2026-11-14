"""The hello agent of the ADK skeleton (T-016).

It calls no model: it greets, counts how many times it ran in this session, and writes both into the session
state. That makes it the cheapest way to prove the runner and the session store work, including that state
written in one run is there in the next, after a restart, when the store is PostgreSQL.
"""
from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from google.genai import types


class HelloAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        runs = int(ctx.session.state.get("hello_runs", 0)) + 1
        text = f"Hello from Verixa ({runs} run{'s' if runs > 1 else ''} in this session)"
        yield Event(invocation_id=ctx.invocation_id, author=self.name,
                    content=types.Content(role="model", parts=[types.Part(text=text)]),
                    actions=EventActions(state_delta={"hello_runs": runs, "greeting": text}))


hello_agent = HelloAgent(name="hello", description="Writes a greeting and a run counter into the session state.")
