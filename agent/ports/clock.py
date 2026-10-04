"""ClockPort: time as a seam (budgets and heartbeats stay testable)."""

import time
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class ClockPort(Protocol):
    """Wall-clock and monotonic time behind one interface."""

    def now(self) -> datetime:
        """Current UTC time (budget deadlines, lease expiry)."""
        ...

    def monotonic(self) -> float:
        """Monotonic seconds (durations, backoff)."""
        ...


class SystemClock:
    """Production clock: real time, no state."""

    def now(self) -> datetime:
        """Current UTC time."""
        return datetime.now(UTC)

    def monotonic(self) -> float:
        """Monotonic seconds."""
        return time.monotonic()
