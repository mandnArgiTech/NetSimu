"""Long-running simulator runtime for the visual lab.

The runtime is owned by the FastAPI app via lifespan. It holds the topology,
runs a baseline counter ticker, and fans out events to any number of
WebSocket subscribers. Each subscriber gets its own bounded asyncio.Queue;
slow consumers are dropped (queue full → silently skip) so one wedged
client never stalls the simulator.

M3 scope: only baseline counters and heartbeats. M4 will plug fault
scenarios into the same publish() pipeline so the WebSocket layer doesn't
need to change.
"""
from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from ..topology import Topology
from .baseline_ticker import BaselineTicker

EventT = dict[str, Any]


class SimRuntime:
    """Owns the live state + the publish pipeline.

    The current snapshot of every entity's counters is kept in
    `self.state[entity_id]` so a freshly-connected WebSocket client can
    receive a complete picture before the next event tick fires.
    """

    def __init__(self, topology: Topology) -> None:
        self.topology = topology
        self.state: dict[str, EventT] = {}
        self._subscribers: list[asyncio.Queue[EventT]] = []
        self._ticker = BaselineTicker(topology, self.publish)
        self._task: asyncio.Task | None = None
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._ticker.seed_state(self.state)
        self._task = asyncio.create_task(self._ticker.run())

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        # Wake any waiting subscribers so the WS handlers can exit.
        for q in self._subscribers:
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait({"kind": "_shutdown"})

    def subscribe(self) -> asyncio.Queue[EventT]:
        # 1000 events buffered per client. At ~50 events/sec this is 20s of
        # backlog before we start dropping — generous for a learning lab.
        q: asyncio.Queue[EventT] = asyncio.Queue(maxsize=1000)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[EventT]) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    def publish(self, event: EventT) -> None:
        """Update the snapshot and fan out to every subscriber."""
        entity_id = event.get("entity")
        if isinstance(entity_id, str):
            self.state[entity_id] = {**self.state.get(entity_id, {}), **event}
        for q in self._subscribers:
            if q.full():
                # Slow client — drop the event for that client only.
                continue
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Race with .full() — same outcome.
                pass

    def snapshot(self) -> dict[str, EventT]:
        """Return a shallow copy of the current per-entity state."""
        return dict(self.state)
