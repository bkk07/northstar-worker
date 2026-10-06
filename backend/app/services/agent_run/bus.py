"""In-process live event bus for AI activity (spec Phase 9 SSE).

Prototype scope: one API process serves SSE subscribers from memory while
the durable timeline lives in `biz.audit_logs` (the UI replays history
from `/trace`, then streams live events here). Multi-worker fan-out is an
explicit non-goal for the prototype.
"""

import asyncio
import time
from collections import defaultdict, deque

_HISTORY: dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
_SUBSCRIBERS: dict[str, set] = defaultdict(set)


def emit(ticket_id: str, event_type: str, data: dict | None = None) -> dict:
    """Publish one activity event (sync-safe; never raises)."""
    event = {
        "ticket_id": str(ticket_id),
        "type": event_type,
        "data": data or {},
        "at": time.time(),
    }
    try:
        _HISTORY[str(ticket_id)].append(event)
        for queue in list(_SUBSCRIBERS.get(str(ticket_id), ())):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass
    except Exception:
        pass
    return event


def subscribe(ticket_id: str) -> asyncio.Queue:
    """Attach a live subscriber (caller must `unsubscribe`)."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _SUBSCRIBERS[str(ticket_id)].add(queue)
    return queue


def unsubscribe(ticket_id: str, queue: asyncio.Queue) -> None:
    """Detach a live subscriber."""
    _SUBSCRIBERS[str(ticket_id)].discard(queue)
