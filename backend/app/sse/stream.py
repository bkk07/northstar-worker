"""Task event stream: backfill, then live tail (Phase 25).

Each event is one audit row framed as SSE (`id` = the gapless `seq`,
so `Last-Event-ID` resume is exact). The generator replays missed rows
from the database first, then tails NOTIFY wakeups — ordering holds
because both paths converge on `seq > last_yielded`.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.schemas.worker.events import AuditEventRead
from app.services.worker.event_service import EventService
from app.sse import listener

BACKFILL_LIMIT = 500
QUEUE_DRAIN = 100
HEARTBEAT_SECONDS = 15.0


def format_event(row: AuditEventRead) -> bytes:
    """One SSE frame: id + named event + JSON data."""
    data = json.dumps(row.model_dump(), default=str)
    return f"id: {row.seq}\nevent: audit\ndata: {data}\n\n".encode()


async def task_event_stream(
    task_id: UUID,
    last_event_id: int,
    session: Session,
    request: Request,
    heartbeat: float = HEARTBEAT_SECONDS,
) -> AsyncIterator[bytes]:
    """Replay missed rows, then tail live wakeups until disconnect."""
    service = EventService(session)
    last_yielded = last_event_id
    for row in service.backfill(task_id, after_seq=last_event_id):
        last_yielded = row.seq
        yield format_event(row)
    queue: asyncio.Queue = asyncio.Queue()
    listener.subscribe(str(task_id), queue)
    try:
        while not await request.is_disconnected():
            try:
                seq = await asyncio.wait_for(queue.get(), timeout=heartbeat)
            except TimeoutError:
                yield b": ping\n\n"
                continue
            for _ in range(QUEUE_DRAIN - 1):
                try:
                    newer = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                seq = max(seq, newer)
            if seq <= last_yielded:
                continue
            row = service.event_by_seq(task_id, seq)
            if row is None:
                continue
            last_yielded = row.seq
            yield format_event(row)
    finally:
        listener.unsubscribe(str(task_id), queue)
