"""Synthesizes baseline counters for entities while no fault is active.

Without this module an idle M3 lab is silent — the canvas renders, the WS
connects, and nothing ever ticks. The ticker generates plausible-looking
numbers (port octets, BGP keepalives, TEP heartbeats) so the user sees
the lab is alive.

When M4 plugs in real fault scenarios, those scenarios will publish their
own events to the same `publish` callback. The ticker keeps emitting
baseline noise so healthy entities continue to show movement.
"""
from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Callable

from ..topology import Topology

EventT = dict[str, Any]
Publish = Callable[[EventT], None]

# How often each kind of event fires. Counters tick every second so
# sparklines feel alive; heartbeats are slower because state rarely
# changes. All times in seconds.
_COUNTER_INTERVAL = 1.0
_HEARTBEAT_INTERVAL = 3.0

# Entity types that produce "data plane" counter events. Logical objects
# (project, vpc, segment, etc.) don't get baseline counters — they have
# no native equivalent until M4 introduces realization-state events.
_COUNTER_TYPES = frozenset({
    "switch",  # spines + ToRs — aggregate of all their ports
    "switch_port",
    "pnic",
    "tep",
    "vm",
    "esx_host",
    "nsx_edge",
})

# Entity types that emit a periodic "still alive" heartbeat with state.
# bgp_session and tep_pair are hidden on the canvas but their state is
# surfaced when the user clicks a participating switch / TEP.
_HEARTBEAT_TYPES = frozenset({
    "bgp_session",
    "tep_pair",
    "tier0",
    "transit_gateway",
})


class BaselineTicker:
    """Async loop that fires synthetic events at a steady cadence.

    The ticker takes a `publish` callback rather than the bus directly so
    the runtime can wrap it with snapshot bookkeeping.
    """

    def __init__(self, topology: Topology, publish: Publish) -> None:
        self.topology = topology
        self.publish = publish
        self._rng = random.Random()
        self._counters: dict[str, dict[str, Any]] = {}

    def seed_state(self, state: dict[str, EventT]) -> None:
        """Populate the runtime's snapshot with an initial entry per
        entity, so a freshly-connected client receives meaningful values
        before the next tick fires."""
        now = time.time()
        for eid, ent in self.topology.entities.items():
            if ent.type in _COUNTER_TYPES:
                init = {
                    "kind": "counters",
                    "entity": eid,
                    "type": ent.type,
                    "ts": now,
                    "bytes_in": self._rng.randint(10_000_000, 50_000_000),
                    "bytes_out": self._rng.randint(10_000_000, 50_000_000),
                    "errors_in": 0,
                    "errors_out": 0,
                    "delta_in": 0,
                    "delta_out": 0,
                }
                self._counters[eid] = init
                state[eid] = init
            elif ent.type in _HEARTBEAT_TYPES:
                state[eid] = {
                    "kind": "heartbeat",
                    "entity": eid,
                    "type": ent.type,
                    "ts": now,
                    "state": "established" if ent.type == "bgp_session" else "ok",
                }

    async def run(self) -> None:
        # Two coroutines, one per cadence. Running them in the same task
        # via gather keeps everything on the runtime's event loop.
        await asyncio.gather(
            self._counter_loop(),
            self._heartbeat_loop(),
        )

    async def _counter_loop(self) -> None:
        while True:
            await asyncio.sleep(_COUNTER_INTERVAL)
            now = time.time()
            for eid, ent in self.topology.entities.items():
                if ent.type not in _COUNTER_TYPES:
                    continue
                base = self._counters.setdefault(eid, {
                    "bytes_in": 0,
                    "bytes_out": 0,
                    "errors_in": 0,
                    "errors_out": 0,
                })
                # Synthetic but realistic: a few hundred kbps of baseline
                # traffic per entity, with mild jitter. No errors at idle.
                lo, hi = self._counter_band(ent.type)
                d_in = self._rng.randint(lo, hi)
                d_out = self._rng.randint(lo, hi)
                base["bytes_in"] += d_in
                base["bytes_out"] += d_out
                self.publish({
                    "kind": "counters",
                    "entity": eid,
                    "type": ent.type,
                    "ts": now,
                    "bytes_in": base["bytes_in"],
                    "bytes_out": base["bytes_out"],
                    "errors_in": base["errors_in"],
                    "errors_out": base["errors_out"],
                    "delta_in": d_in,
                    "delta_out": d_out,
                })

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(_HEARTBEAT_INTERVAL)
            now = time.time()
            for eid, ent in self.topology.entities.items():
                if ent.type not in _HEARTBEAT_TYPES:
                    continue
                state = "established" if ent.type == "bgp_session" else "ok"
                self.publish({
                    "kind": "heartbeat",
                    "entity": eid,
                    "type": ent.type,
                    "ts": now,
                    "state": state,
                })

    def _counter_band(self, etype: str) -> tuple[int, int]:
        # Bytes-per-second bands by role. Switches and ESX hosts roll up
        # all their ports/pNICs — wider band to reflect that. Spines see
        # more aggregate traffic than ToRs because every inter-rack flow
        # crosses a spine.
        if etype == "switch":
            return 1_000_000, 8_000_000
        if etype in ("switch_port", "pnic"):
            return 50_000, 500_000
        if etype == "tep":
            return 30_000, 300_000
        if etype == "esx_host":
            return 200_000, 1_500_000
        if etype == "nsx_edge":
            return 100_000, 800_000
        return 5_000, 50_000  # vm and fallback
