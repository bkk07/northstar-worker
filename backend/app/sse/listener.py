"""LISTEN/NOTIFY bridge: Postgres shouts, asyncio queues hear it.

One daemon thread holds a single `LISTEN worker_audit_events`
connection and routes each notification to the subscriber queues
`stream.py` registered for that task. The thread never touches
asyncio objects directly — wakeups cross via `loop.call_soon_threadsafe`.
"""

import asyncio
import logging
import threading

_LOGGER = logging.getLogger("northstar.sse")

CHANNEL = "worker_audit_events"

_lock = threading.Lock()
_thread: threading.Thread | None = None
_stop = threading.Event()
_subscribers: dict[str, list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]]] = {}


def subscribe(task_id: str, queue: asyncio.Queue) -> None:
    """Register one stream's queue; starts the listener thread on demand."""
    loop = asyncio.get_running_loop()
    with _lock:
        _subscribers.setdefault(task_id, []).append((loop, queue))
        _ensure_started_locked()


def unsubscribe(task_id: str, queue: asyncio.Queue) -> None:
    """Drop one stream's queue (client disconnect cleanup)."""
    with _lock:
        pairs = _subscribers.get(task_id, [])
        _subscribers[task_id] = [(loop, other) for loop, other in pairs if other is not queue]
        if not _subscribers[task_id]:
            _subscribers.pop(task_id, None)


def subscriber_count(task_id: str | None = None) -> int:
    """Registered queues, optionally for one task (disconnect tests)."""
    with _lock:
        if task_id is not None:
            return len(_subscribers.get(task_id, []))
        return sum(len(pairs) for pairs in _subscribers.values())


def _ensure_started_locked() -> None:
    """One daemon listener per process (idempotent)."""
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_listen_forever, name="sse-notify-listener", daemon=True)
    _thread.start()


def _route(task_id: str, seq: int) -> None:
    """Wake every queue subscribed to the task (thread-safe hop)."""
    with _lock:
        pairs = list(_subscribers.get(task_id, []))
    for loop, queue in pairs:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, seq)
        except RuntimeError:
            continue


def _listen_forever() -> None:
    """Blocking NOTIFY loop (dies loudly; the next subscribe restarts it)."""
    import psycopg

    from database.session import role_url

    url = role_url("ns_app").replace("postgresql+psycopg://", "postgresql://", 1)
    try:
        with psycopg.connect(url, autocommit=True) as connection:
            connection.execute(f"LISTEN {CHANNEL};")
            while not _stop.is_set():
                # Fresh generator per wait: `notifies()` ends after the
                # timeout, so reusing one would miss every later NOTIFY.
                for notify in connection.notifies(timeout=1.0):
                    try:
                        task_id, _, raw_seq = notify.payload.partition(":")
                        _route(task_id, int(raw_seq))
                    except (ValueError, AttributeError):
                        _LOGGER.warning("sse: ignoring malformed notify %r", notify.payload)
    except Exception:
        _LOGGER.exception("sse: notify listener died")
