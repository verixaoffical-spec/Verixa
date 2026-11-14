"""model_calls logging (T-026): every model attempt the agents trace becomes one row.

The agents never touch the database. They already trace each attempt (analysis.model_answered / model_failed for
the Analysis Agent's ADK writers, llm.model_answered / model_failed for agents.llm.ask). This listener turns those
lines into rows. Writing happens on one background thread, so an agent never waits for the database, and a failed
write is logged and dropped: losing a log row must never break an analysis.
"""
import logging
import queue
import threading

from .agent_db import ModelCall
from .db import SessionLocal

log = logging.getLogger(__name__)
EVENTS = {"analysis.model_answered": ("analysis", True), "analysis.model_failed": ("analysis", False),
          "llm.model_answered": (None, True), "llm.model_failed": (None, False)}
_queue: queue.Queue = queue.Queue(maxsize=1000)
_worker: threading.Thread | None = None


def _int(value) -> int | None:
    try:
        return int(value) if value not in (None, "", "None") else None
    except (TypeError, ValueError):
        return None


def to_row(line: dict) -> dict | None:
    """The model_calls columns for one trace line, or None for lines that are not a model attempt."""
    kind = EVENTS.get(line.get("event"))
    if not kind:
        return None
    agent, ok = kind
    model = str(line.get("model") or "")
    return {"agent": (agent or str(line.get("task") or "unknown"))[:40], "model": model[:120],
            "provider": model.split("/", 1)[0][:40] if "/" in model else "unknown",
            "tokens": _int(line.get("tokens")), "latency_ms": _int(line.get("ms")), "ok": ok,
            "error": None if ok else str(line.get("error") or "")[:300] or None, "run_id": line.get("run_id")}


def _write_forever() -> None:
    while True:
        row = _queue.get()
        try:
            with SessionLocal() as db:
                db.add(ModelCall(**row))
                db.commit()
        except Exception as exc:
            log.warning("model_calls: could not write a row (%s)", type(exc).__name__)
        finally:
            _queue.task_done()


def record(line: dict) -> None:
    """Trace listener. Cheap and never raises: it only queues the row."""
    global _worker
    row = to_row(line)
    if row is None:
        return
    if _worker is None or not _worker.is_alive():
        _worker = threading.Thread(target=_write_forever, name="model-calls-writer", daemon=True)
        _worker.start()
    try:
        _queue.put_nowait(row)
    except queue.Full:
        log.warning("model_calls: queue full, a row was dropped")


def flush(timeout: float = 10.0) -> bool:
    """Waits until every queued row is written (tests and checks). True when the queue drained in time."""
    done = threading.Event()
    threading.Thread(target=lambda: (_queue.join(), done.set()), daemon=True).start()
    return done.wait(timeout)
