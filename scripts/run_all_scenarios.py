#!/usr/bin/env python3
"""Run all 6 scenarios and produce a summary table.

Use this as the regression test for an RCA engine: pipe each archive into
your engine, capture its output as RCA JSON, then call grading.grade()
on each (rca, truth) pair. This script just verifies the simulator side
end-to-end.
"""
from __future__ import annotations

import asyncio
import os

from netops_sim.runner import run_scenario
from netops_sim.scenarios import SCENARIOS


SCENARIO_DURATIONS = {
    "mtu_mismatch": 400.0,
    "bgp_flap": 400.0,
    "silent_packet_loss": 600.0,
    "tep_ip_collision": 400.0,
    "dfw_rule_break": 400.0,
    "pnic_failure_vmotion": 400.0,
}


async def main():
    out_dir = "./runs"
    os.makedirs(out_dir, exist_ok=True)

    print(f"{'Scenario':<25} {'Difficulty':<10} {'Events':>8} {'Archive':<40}")
    print("-" * 90)

    results = []
    for name in sorted(SCENARIOS):
        duration = SCENARIO_DURATIONS.get(name, 400.0)
        archive_path, truth = await run_scenario(
            name, real_time=False, out_dir=out_dir,
            duration_seconds=duration, distractors=True, snapshots=True,
            seed=42,
        )
        # Quickly count events
        with open(archive_path) as f:
            event_count = sum(1 for _ in f)
        difficulty = truth.get("difficulty", "?")
        results.append((name, difficulty, event_count, os.path.basename(archive_path)))
        print(f"{name:<25} {difficulty:<10} {event_count:>8} {os.path.basename(archive_path):<40}")

    print("-" * 90)
    total_events = sum(r[2] for r in results)
    print(f"\n{len(results)} scenarios, {total_events} total events archived to {out_dir}/")
    print("\nNext step: pipe each .jsonl into your RCA engine and grade against the .truth.json.")
    print("  python -m netops_sim.grading <rca_output>.json <scenario>.truth.json")


if __name__ == "__main__":
    asyncio.run(main())
