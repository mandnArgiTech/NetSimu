"""Discrete-event virtual clock.

The clock advances by either:
  - Pulling the next scheduled callback from a priority queue (fast simulation), or
  - Sleeping in real time before firing it (real-time mode for demos).

Everything time-related in NetSimu uses this clock — not datetime.now() or
asyncio.sleep() directly. That guarantees determinism in tests.
"""
from __future__ import annotations

import asyncio
import heapq
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable

CallbackT = Callable[[], Awaitable[None]] | Callable[[], None]


@dataclass(order=True)
class _Scheduled:
    when: float
    seq: int
    cb: CallbackT = field(compare=False)


class VirtualClock:
    """Discrete-event clock. Optionally syncs to wall clock for demos."""

    def __init__(self, start: datetime | None = None, real_time: bool = False):
        start = start or datetime(2026, 5, 5, 14, 0, tzinfo=timezone.utc)
        self._t: float = start.timestamp()
        self._real_time = real_time
        self._queue: list[_Scheduled] = []
        self._seq = 0
        self._stopped = False

    def now(self) -> datetime:
        return datetime.fromtimestamp(self._t, tz=timezone.utc)

    def now_ts(self) -> float:
        return self._t

    def schedule(self, delay: float, cb: CallbackT) -> None:
        """Schedule callback to fire after `delay` simulated seconds."""
        if delay < 0:
            delay = 0
        self._seq += 1
        heapq.heappush(self._queue, _Scheduled(self._t + delay, self._seq, cb))

    def at(self, when: datetime, cb: CallbackT) -> None:
        self.schedule(when.timestamp() - self._t, cb)

    async def run_until(self, end_ts: float) -> None:
        """Drain the queue until either empty or end_ts is reached."""
        steps_since_yield = 0
        while self._queue and not self._stopped:
            ev = self._queue[0]
            if ev.when > end_ts:
                self._t = end_ts
                # Final yield so any tasks awaiting just-resolved futures
                # get scheduled before drain returns.
                await asyncio.sleep(0)
                return
            heapq.heappop(self._queue)

            if self._real_time:
                wait = ev.when - self._t
                if wait > 0:
                    await asyncio.sleep(wait)
            self._t = ev.when

            result = ev.cb()
            if asyncio.iscoroutine(result):
                await result

            # Yield to the asyncio loop periodically so that other tasks
            # (notably scenarios awaiting futures we've resolved) get to run.
            steps_since_yield += 1
            if steps_since_yield >= 32:
                await asyncio.sleep(0)
                steps_since_yield = 0
        self._t = end_ts
        await asyncio.sleep(0)

    def stop(self) -> None:
        self._stopped = True

    @property
    def queue_size(self) -> int:
        return len(self._queue)
