"""Tests for topology snapshots and as-of materialization."""
from __future__ import annotations

import pytest

from netops_sim.bus import EventBus
from netops_sim.clock import VirtualClock
from netops_sim.snapshots import (
    TopologySnapshotter,
    find_snapshot_at,
    materialize_topology,
    serialize_topology,
)
from netops_sim.topology import build_reference_topology


def test_serialize_includes_all_entities_and_edges():
    topo = build_reference_topology()
    snap = serialize_topology(topo)
    assert len(snap["nodes"]) == len(topo.entities)
    assert len(snap["edges"]) == topo.g.number_of_edges()
    # Spot-check a node
    web_vm = next(n for n in snap["nodes"] if n["id"] == "vm-web-01")
    assert web_vm["type"] == "vm"
    assert web_vm["layer"] == "application"


def test_materialize_round_trip():
    topo = build_reference_topology()
    snap = {"graph": serialize_topology(topo), "ts": 0, "snapshot_id": 1}
    rebuilt = materialize_topology(snap)
    assert rebuilt.stats() == topo.stats()
    # Verify a key dependency edge survived
    deps = list(rebuilt.neighbors("app-web", "depends_on"))
    assert "app-api" in deps


@pytest.mark.asyncio
async def test_snapshotter_emits_on_interval():
    clock = VirtualClock()
    topo = build_reference_topology()
    bus = EventBus()

    events: list[dict] = []
    bus.subscribe(None, events.append)

    snap = TopologySnapshotter(interval_seconds=20.0)
    snap.start(clock, topo, bus)

    await clock.run_until(clock.now_ts() + 100)

    snapshots = [e for e in events if e.get("kind") == "topology_snapshot"]
    # Should have ~5 snapshots in 100 sim seconds at 20s interval
    assert 4 <= len(snapshots) <= 6


def test_find_snapshot_at_picks_latest_eligible():
    snapshots = [
        {"ts": 10, "graph": {"nodes": [], "edges": []}},
        {"ts": 30, "graph": {"nodes": [{"id": "a"}], "edges": []}},
        {"ts": 50, "graph": {"nodes": [], "edges": []}},
    ]
    s = find_snapshot_at(snapshots, target_ts=35)
    assert s is not None and s["ts"] == 30

    s = find_snapshot_at(snapshots, target_ts=50)
    assert s is not None and s["ts"] == 50

    s = find_snapshot_at(snapshots, target_ts=5)
    assert s is None
