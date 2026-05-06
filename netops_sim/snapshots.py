"""Topology snapshots — periodic dumps of the graph state for as-of queries.

The simulator's `Topology` is a current-view object. For RCA testing you
sometimes need the graph state *as it was at incident time*, especially if
the scenario includes structural changes (vMotion, VPC create, etc.).

This module emits snapshot events to the bus periodically, and offers a
helper to materialize the graph back from a snapshot stream.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .bus import EventBus
    from .clock import VirtualClock
    from .topology import Topology


def serialize_topology(topo: "Topology") -> dict[str, Any]:
    """Serialize the current topology to a JSON-safe dict."""
    nodes = []
    for e in topo.entities.values():
        nodes.append({
            "id": e.id,
            "type": e.type,
            "layer": e.layer,
            "vendor": e.vendor,
            "attrs": dict(e.attrs),
            "state": {
                k: v for k, v in e.state.items()
                if isinstance(v, (str, int, float, bool, type(None)))
            },
        })
    edges = []
    for src, dst, key, data in topo.g.edges(keys=True, data=True):
        edges.append({
            "src": src,
            "dst": dst,
            "rel": key,
            "attrs": {
                k: v for k, v in data.items()
                if isinstance(v, (str, int, float, bool, type(None)))
                and k != "rel"
            },
        })
    return {"nodes": nodes, "edges": edges}


class TopologySnapshotter:
    """Periodically emits topology snapshots to the bus.

    Snapshots arrive as `kind=topology_snapshot` events with a complete
    serialization. Light-weight enough for the reference 100-entity graph;
    if you scale up significantly, switch to delta encoding.
    """

    def __init__(self, interval_seconds: float = 30.0):
        self.interval = interval_seconds
        self._snapshot_count = 0

    def start(self, clock: "VirtualClock", topo: "Topology", bus: "EventBus") -> None:
        # First snapshot at t=1 (after initial setup)
        clock.schedule(1.0, lambda: self._tick(clock, topo, bus))

    def _tick(self, clock: "VirtualClock", topo: "Topology", bus: "EventBus") -> None:
        self._snapshot_count += 1
        bus.publish({
            "ts": clock.now_ts(),
            "source": "topology_snapshotter",
            "kind": "topology_snapshot",
            "snapshot_id": self._snapshot_count,
            "graph": serialize_topology(topo),
            "stats": topo.stats(),
        })
        clock.schedule(self.interval, lambda: self._tick(clock, topo, bus))


def attach_snapshotter(
    clock: "VirtualClock",
    topo: "Topology",
    bus: "EventBus",
    interval_seconds: float = 30.0,
) -> TopologySnapshotter:
    snap = TopologySnapshotter(interval_seconds=interval_seconds)
    snap.start(clock, topo, bus)
    return snap


# ────────────────────────────────────────────────────────────────────────────
# Replay-side helpers — reconstruct topology at a point in time
# ────────────────────────────────────────────────────────────────────────────
def find_snapshot_at(
    snapshots: list[dict[str, Any]], target_ts: float
) -> dict[str, Any] | None:
    """Pick the latest snapshot whose ts <= target_ts.

    Use case: an RCA engine reading the JSONL archive wants to know the
    topology shape at the moment of the incident. Filter the archive for
    `kind=topology_snapshot`, pass the list here with the incident timestamp.
    """
    eligible = [s for s in snapshots if s.get("ts", 0) <= target_ts]
    if not eligible:
        return None
    return max(eligible, key=lambda s: s["ts"])


def materialize_topology(snapshot: dict[str, Any]):
    """Rebuild a Topology object from a snapshot dict. Useful for tests."""
    from .topology import Entity, Topology

    topo = Topology()
    graph = snapshot.get("graph", {})
    for n in graph.get("nodes", []):
        topo.add(Entity(
            id=n["id"], type=n["type"], layer=n["layer"],
            vendor=n.get("vendor", ""), attrs=n.get("attrs", {}),
            state=n.get("state", {}),
        ))
    for e in graph.get("edges", []):
        if e["src"] in topo.entities and e["dst"] in topo.entities:
            topo.link(e["src"], e["dst"], e["rel"], **e.get("attrs", {}))
    return topo
