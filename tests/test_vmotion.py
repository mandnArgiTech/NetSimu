"""Tests for vMotion helpers — VM-host edge mutation."""
from __future__ import annotations

from netops_sim.bus import EventBus
from netops_sim.clock import VirtualClock
from netops_sim.topology import build_reference_topology
from netops_sim.vmotion import evacuate_host, vmotion


def test_vmotion_changes_runs_on_edge():
    topo = build_reference_topology()
    bus = EventBus()
    clock = VirtualClock()

    # vm-web-01 starts on host-01
    initial_host = next(topo.neighbors("vm-web-01", "runs_on"))
    assert initial_host == "host-01"

    ok = vmotion("vm-web-01", "host-04", topo, bus, clock)
    assert ok

    new_host = next(topo.neighbors("vm-web-01", "runs_on"))
    assert new_host == "host-04"
    # Old edge gone
    edges_to_old = list(topo.g.get_edge_data("vm-web-01", initial_host) or {})
    assert "runs_on" not in edges_to_old


def test_vmotion_emits_event():
    topo = build_reference_topology()
    bus = EventBus()
    clock = VirtualClock()

    events: list[dict] = []
    bus.subscribe(None, events.append)

    vmotion("vm-web-01", "host-04", topo, bus, clock, reason="test")

    vmotion_events = [e for e in events if e.get("kind") == "vmotion"]
    assert len(vmotion_events) == 1
    assert vmotion_events[0]["from_host"] == "host-01"
    assert vmotion_events[0]["to_host"] == "host-04"
    assert vmotion_events[0]["reason"] == "test"


def test_evacuate_host_moves_all_vms():
    topo = build_reference_topology()
    bus = EventBus()
    clock = VirtualClock()

    # host-01 has vm-web-01 and vm-api-01
    vms_on_01 = list(topo.predecessors("host-01", "runs_on"))
    assert "vm-web-01" in vms_on_01

    moves = evacuate_host("host-01", topo, bus, clock)

    assert len(moves) == len(vms_on_01)
    moved_vms = {vm for vm, _ in moves}
    assert moved_vms == set(vms_on_01)

    # No VM should still be on host-01
    leftover = list(topo.predecessors("host-01", "runs_on"))
    assert leftover == []


def test_vmotion_rejects_unknown_entities():
    topo = build_reference_topology()
    bus = EventBus()
    clock = VirtualClock()

    assert not vmotion("vm-fake", "host-01", topo, bus, clock)
    assert not vmotion("vm-web-01", "host-fake", topo, bus, clock)
