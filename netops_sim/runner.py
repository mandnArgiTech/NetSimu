"""Main scenario runner.

Wires together: clock + topology + behaviors + bus + archive sink + scenario.
Optionally adds distractor noise generator and topology snapshotter.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any

from .bus import EventBus
from .clock import VirtualClock
from .distractors import DistractorConfig, attach_distractors
from .entities import BEHAVIORS, instantiate_behaviors
from .physics import app_impact_tick
from .scenarios import SCENARIOS
from .snapshots import attach_snapshotter
from .topology import build_reference_topology


def _serialize(obj: Any) -> Any:
    """JSON serializer for unhandled types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "now_ts"):  # VirtualClock — strip from events
        return None
    return str(obj)


async def run_scenario(
    name: str,
    real_time: bool = False,
    out_dir: str = "./runs",
    duration_seconds: float = 600.0,
    distractors: bool = True,
    distractor_rate: float = 2.0,
    snapshots: bool = True,
    snapshot_interval: float = 30.0,
    seed: int | None = None,
) -> tuple[str, dict]:
    if name not in SCENARIOS:
        raise ValueError(
            f"Unknown scenario {name!r}. Available: {sorted(SCENARIOS)}"
        )

    clock = VirtualClock(real_time=real_time)
    topo = build_reference_topology()
    bus = EventBus()

    print(f"[runner] topology: {topo.stats()}")

    instantiate_behaviors(topo)
    print(f"[runner] instantiated {len(BEHAVIORS)} behaviors")

    # Subscribe each behavior to all events
    for beh in BEHAVIORS.values():
        bus.subscribe(None, lambda ev, b=beh: b.on_event(ev, topo, bus))

    # Periodic ticks: behaviors + app-impact
    def _schedule_recurring(clock, topo, bus, beh, interval) -> None:
        async def fire():
            await beh.tick(clock, topo, bus)
            clock.schedule(interval, fire)
        clock.schedule(0.5, fire)

    for beh in BEHAVIORS.values():
        tick_interval = getattr(beh, "TICK_SECONDS", 10.0)
        _schedule_recurring(clock, topo, bus, beh, tick_interval)

    def schedule_app_impact() -> None:
        async def fire():
            app_impact_tick(clock, topo, bus)
            clock.schedule(15.0, fire)
        clock.schedule(5.0, fire)

    schedule_app_impact()

    # Optional: distractor noise generator
    if distractors:
        # Exclude the immediate root cause vicinity from distractors.
        # We don't know the exact target until the scenario runs, but we
        # can be conservative — distractors only fire on hosts/VMs.
        # The root cause for our scenarios is typically a port/edge entity,
        # so the exclusion list can be empty. (Override per-scenario if needed.)
        d_cfg = DistractorConfig(rate_per_minute=distractor_rate, seed=seed)
        attach_distractors(clock, topo, bus, config=d_cfg)
        print(f"[runner] distractors ON (rate={distractor_rate}/min)")

    # Optional: topology snapshotter
    if snapshots:
        attach_snapshotter(clock, topo, bus, interval_seconds=snapshot_interval)
        print(f"[runner] snapshots ON (every {snapshot_interval}s)")

    # Archive sink
    os.makedirs(out_dir, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_path = os.path.join(out_dir, f"{name}-{run_id}.jsonl")
    truth_path = os.path.join(out_dir, f"{name}-{run_id}.truth.json")

    archive = open(archive_path, "w")

    def write_event(ev: dict) -> None:
        clean = {k: v for k, v in ev.items() if k != "clock"}
        archive.write(json.dumps(clean, default=_serialize) + "\n")

    bus.subscribe(None, write_event)

    # Run scenario alongside the clock drain. Give drain a buffer beyond
    # the scenario's needed duration so resolve callbacks fire reliably.
    end_t = clock.now_ts() + duration_seconds + 60.0
    scn_fn = SCENARIOS[name]

    scenario_task = asyncio.create_task(scn_fn(clock, topo, bus))
    drain_task = asyncio.create_task(clock.run_until(end_t))

    truth = await scenario_task
    await drain_task

    archive.close()
    with open(truth_path, "w") as f:
        json.dump(truth, f, indent=2, default=_serialize)

    print(f"[runner] events emitted: {bus.published_count}")
    print(f"[runner] archive   → {archive_path}")
    print(f"[runner] truth     → {truth_path}")
    return archive_path, truth


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a NetSimu scenario.")
    parser.add_argument("scenario", choices=sorted(SCENARIOS),
                        help="Scenario name")
    parser.add_argument("--real-time", action="store_true",
                        help="Sync clock to wall time (for live demos)")
    parser.add_argument("--out", default="./runs",
                        help="Output directory for archive + truth")
    parser.add_argument("--duration", type=float, default=600.0,
                        help="Simulated seconds to run (default 600)")
    parser.add_argument("--no-distractors", action="store_true",
                        help="Disable distractor noise generation")
    parser.add_argument("--distractor-rate", type=float, default=2.0,
                        help="Distractor anomalies per minute (default 2.0)")
    parser.add_argument("--no-snapshots", action="store_true",
                        help="Disable periodic topology snapshots")
    parser.add_argument("--snapshot-interval", type=float, default=30.0,
                        help="Seconds between topology snapshots")
    parser.add_argument("--seed", type=int, default=None,
                        help="RNG seed for reproducibility")
    args = parser.parse_args()

    asyncio.run(run_scenario(
        args.scenario, args.real_time, args.out, args.duration,
        distractors=not args.no_distractors,
        distractor_rate=args.distractor_rate,
        snapshots=not args.no_snapshots,
        snapshot_interval=args.snapshot_interval,
        seed=args.seed,
    ))


if __name__ == "__main__":
    main()
