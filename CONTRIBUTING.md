# Contributing

## Local dev setup

```bash
git clone https://github.com/mandnArgiTech/NetSimu.git
cd NetSimu
python -m venv .venv && source .venv/bin/activate
make dev          # installs package + dev deps
make test         # should be all green in <1s
```

## What to work on (open issues / good first projects)

- **More scenarios:** TEP IP collision, DFW rule misorder, pNIC failure with vMotion cascade.
- **Stochastic distractor anomalies:** noise generators (CPU spikes, disk latency) that fire alongside real faults to test discrimination.
- **gRPC gNMI server:** replace the WebSocket shim with `pygnmi`-based real gNMI Subscribe.
- **VM mobility:** scenarios that vMotion a VM mid-fault and verify the topology updates.
- **Topology scale:** parametric topology builder (32 hosts, 8 ToRs).
- **Real-time mode polish:** smooth visualization for live demos.

## Code style

- Python 3.11+, type hints required on public functions.
- `ruff format` + `ruff check` on commit.
- No global mutable state outside `BEHAVIORS` registry and `audit_buffer` (both clearly scoped).
- Tests required for new behaviors and scenarios.

## Adding a scenario

1. Write an async function in `netops_sim/scenarios.py`:
   ```python
   async def scenario_tep_collision(clock, topo, bus):
       await _wait(clock, 60)
       inject_fault(bus, clock, target="tep-host-01", fault_type="ip_collision")
       await _wait(clock, 240)
       return {"scenario": "tep_collision", "root_cause_entity": "tep-host-01", ...}
   ```
2. Register in `SCENARIOS = {...}`.
3. If new fault type, extend the relevant `Behavior.on_event`.
4. Add an integration test under `tests/test_scenarios.py`.

## Adding a vendor mock

1. Create `netops_sim/emitters/<vendor>.py` with a FastAPI app.
2. Map your real vendor's API surface — return JSON shapes that match the real device.
3. Read state from `BEHAVIORS` (entities populated by the runner).
4. Add to `serve_all.py` so it boots with the others.

## RCA-engine contract

Output JSON must have:
```json
{
  "incident_id": "INC-YYYY-MM-DD-NNNN",
  "ranked_hypotheses": [
    {"entity_id": "...", "score": 0.0, "rule": "R-XXX-NNN"},
    ...
  ],
  "matched_anomalies": [
    {"entity": "...", "metric": "..."},
    ...
  ]
}
```

Run `python -m netops_sim.grading rca.json truth.json` to score.
