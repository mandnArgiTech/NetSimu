#!/usr/bin/env python3
"""End-to-end demo: run a scenario, build a fake RCA output, grade it.

This shows the contract your real RCA engine needs to satisfy:
  input  = JSONL telemetry archive
  output = ranked_hypotheses + matched_anomalies (see grading.py for schema)
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile

from netops_sim.grading import grade
from netops_sim.runner import run_scenario


async def main():
    print(">>> Running scenario...")
    archive_path, truth = await run_scenario(
        "mtu_mismatch", real_time=False, out_dir="./runs", duration_seconds=400.0
    )

    # ── In real life, your RCA engine reads `archive_path`, runs anomaly
    #    detection + topology projection + Bayesian scoring, and outputs:
    fake_rca = {
        "incident_id": "INC-DEMO-0001",
        "ranked_hypotheses": [
            {"entity_id": "port-tor-01-host-01-vmnic0",
             "score": 0.91, "rule": "R-MTU-001"},
            {"entity_id": "port-tor-03-host-01-vmnic1", "score": 0.42},
            {"entity_id": "tep-host-01", "score": 0.05},
            {"entity_id": "vlan-1647", "score": 0.02},
        ],
        "matched_anomalies": [
            {"entity": "port-tor-01-host-01-vmnic0", "metric": "in_errors"},
            {"entity": "teppair-host-01-host-02", "metric": "drop_pps"},
            {"entity": "tep-host-01", "metric": "encap_errors"},
            {"entity": "app-web", "metric": "p99_latency_ms"},
            {"entity": "app-web", "metric": "5xx_rate"},
        ],
    }

    # Write to a temp file and grade it
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(fake_rca, f, indent=2)
        rca_path = f.name

    truth_path = archive_path.replace(".jsonl", ".truth.json")
    print(f"\n>>> Grading RCA output against {os.path.basename(truth_path)}...")
    result = grade(rca_path, truth_path)
    print(json.dumps(result, indent=2))

    os.unlink(rca_path)


if __name__ == "__main__":
    asyncio.run(main())
