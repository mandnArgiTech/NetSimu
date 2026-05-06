"""Tests for the distractor noise generator."""
from __future__ import annotations

import asyncio

import pytest

from netops_sim.bus import EventBus
from netops_sim.clock import VirtualClock
from netops_sim.distractors import DistractorConfig, DistractorNoiseGenerator
from netops_sim.entities import instantiate_behaviors
from netops_sim.topology import build_reference_topology


@pytest.mark.asyncio
async def test_distractors_emit_during_window():
    clock = VirtualClock()
    topo = build_reference_topology()
    bus = EventBus()
    instantiate_behaviors(topo)

    events: list[dict] = []
    bus.subscribe(None, events.append)

    # High rate so we definitely see some over a short window
    cfg = DistractorConfig(rate_per_minute=20.0, seed=42)
    gen = DistractorNoiseGenerator(config=cfg)
    gen.start(clock, topo, bus)

    await clock.run_until(clock.now_ts() + 600)

    distractor_starts = [e for e in events if e.get("kind") == "distractor_start"]
    metric_events = [
        e for e in events
        if e.get("source") == "distractor"
        or e.get("kind") in ("host_metric", "vm_metric")
    ]

    assert len(distractor_starts) >= 5, \
        f"Expected at least 5 distractors in 10 sim minutes, got {len(distractor_starts)}"
    assert len(metric_events) > len(distractor_starts), \
        "Each distractor should emit multiple datapoints"


@pytest.mark.asyncio
async def test_distractor_categories_distribute():
    clock = VirtualClock()
    topo = build_reference_topology()
    bus = EventBus()
    instantiate_behaviors(topo)

    events: list[dict] = []
    bus.subscribe(None, events.append)

    cfg = DistractorConfig(
        rate_per_minute=30.0,
        cpu_prob=0.5, disk_prob=0.3, mem_prob=0.2,
        seed=123,
    )
    gen = DistractorNoiseGenerator(config=cfg)
    gen.start(clock, topo, bus)

    await clock.run_until(clock.now_ts() + 1200)

    starts = [e for e in events if e.get("kind") == "distractor_start"]
    cats = {s.get("category") for s in starts}
    # Over 20 minutes with random sampling, at least 2 categories should appear
    assert len(cats) >= 2, f"Expected category mix, got {cats}"


@pytest.mark.asyncio
async def test_excluded_entities_skipped():
    clock = VirtualClock()
    topo = build_reference_topology()
    bus = EventBus()
    instantiate_behaviors(topo)

    events: list[dict] = []
    bus.subscribe(None, events.append)

    excluded = {"host-01", "host-02", "vm-web-01"}
    cfg = DistractorConfig(rate_per_minute=30.0, seed=7)
    gen = DistractorNoiseGenerator(config=cfg, excluded_entities=excluded)
    gen.start(clock, topo, bus)

    await clock.run_until(clock.now_ts() + 1200)

    starts = [e for e in events if e.get("kind") == "distractor_start"]
    targeted = {s.get("entity") for s in starts}

    assert len(starts) > 0, "Should still produce distractors"
    assert excluded.isdisjoint(targeted), \
        f"Excluded entities should not be targeted: {targeted & excluded}"
