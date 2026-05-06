# NetSimu

A pure-software simulator for VCF/NSX + multi-vendor underlay network topologies. Generates realistic telemetry streams (counters, BGP state, syslog, NSX Policy API, gNMI) for developing and testing next-generation NetOps / RCA platforms — without requiring real hardware, vendor images, or container labs.

NetSimu was built to be the regression-test bed for an RCA engine that performs root-cause analysis across overlay (NSX/VCF) and multi-vendor underlay (Cisco, Arista) layers using rule-augmented Bayesian inference, GNNs, and embedding-based retrieval.

## Why pure-software simulation

Container-lab + cEOS + Nexus 9000v setups are powerful but heavy: they require licenses or images you may not have, eat memory, and are slow to iterate against. For an RCA platform PoC you don't need real switch software — you need realistic *telemetry streams*. NetSimu models the patterns: per-port counters, MTU mismatches, BGP flaps, Geneve drops, app-layer cascades, config diffs.

Everything runs in one Python process. Simulate four hours of operation in 30 seconds, or slow to wall-clock for demos.

## Quickstart

```bash
# Install
pip install -e .

# Run the MTU-mismatch scenario, archive telemetry to JSONL
python -m netops_sim.runner mtu_mismatch

# Or run all scenarios
make sim-all

# Replay a recorded run at 10× speed
python -m netops_sim.replay runs/mtu_mismatch-20260505T143200Z.jsonl --speed 10

# Spin up the mock APIs (NSX, NX-API, gNMI WebSocket) for live integration testing
make mocks
```

## Reference topology

```
              spine-01            spine-02         (Arista 7280)
                  │ │ │ │            │ │ │ │
              ┌───┴─┼─┼─┴───┐    ┌───┴─┼─┼─┴───┐
            tor-01 tor-02 tor-03 tor-04           (Cisco N9K + Arista 7050)
              │      │      │      │
        ┌─────┼──────┼──────┼──────┼──────┐
      host-01 host-02 host-03 host-04 ... host-08  (8 ESX, 3 clusters)
        │
   ┌────┴────┐
  TEP    pNICs (vmnic0/1, dual-homed)
   │
   └─→ NSX overlay: 1 T0, 1 TGW, 1 Project, 3 VPCs, 4 segments
        │
       VMs: vm-web-{01..03}, vm-api-{01..02}, vm-db-{01..02}
        │
       Apps: app-web → app-api → app-db
```

~150 entities, ~400 edges. Mirrors a small real VCF deployment.

## Built-in fault scenarios

| Scenario | What it injects | Difficulty | Notable |
|---|---|---|---|
| `mtu_mismatch` | ToR host-port MTU 9216 → 1500 (both bonded uplinks) | Easy | Geneve drops + app cascade |
| `bgp_flap` | T0 BGP neighbor goes Idle for 45s | Medium | Routing churn |
| `silent_packet_loss` | 0.3% CRC errors on spine-tor link | Hard | No link-down |
| `tep_ip_collision` | Stale TEP IP after host re-add | Medium | Clean underlay, DUP_IP syslog only |
| `dfw_rule_break` | DFW rule allow → deny, breaks app tier | Hard | No infra errors, only audit + app |
| `pnic_failure_vmotion` | Both pNICs on host-03 fail; HA evacuates | Medium | Topology mutates mid-incident |

Each scenario emits a ground-truth file naming the actual root cause, the expected anomalies, and the rule that should fire. This is what you grade your RCA engine against.

## Realism features

**Distractor noise** (`--distractor-rate N`): random CPU spikes on hosts, disk-I/O bursts on VMs, memory pressure events. Defaults to 2/minute. Forces RCA to discriminate signal from noise. Disable with `--no-distractors`.

**Topology snapshots** (`--snapshot-interval N`): periodic full-graph dumps to the archive. Lets RCA engines reconstruct the topology *as of incident time*, especially important when the scenario itself mutates the graph (vMotion, VPC create). Disable with `--no-snapshots`.

**Reproducibility** (`--seed N`): all RNG sources accept a seed for byte-exact reproduction.

## Architecture

```
                            ┌───────────────────────┐
                            │   Fault Injector      │
                            │   (scenarios.py)      │
                            └───────────┬───────────┘
                                        │
                   ┌────────────────────┴───────────────────┐
                   ▼                                        ▼
         ┌──────────────────┐                  ┌─────────────────────┐
         │  Topology graph  │                  │   Event Bus         │
         │  (networkx)      │                  │   (in-memory)       │
         └─────────┬────────┘                  └────────┬────────────┘
                   │                                    │
                   ▼                                    │
         ┌──────────────────┐                           │
         │  Behaviors       │  state machines per       │
         │  per entity      │  switch_port, tep, bgp,   │
         │  (ticking)       │  app, ...                 │
         └─────────┬────────┘                           │
                   │                                    │
                   └────────────────┬───────────────────┘
                                    ▼
                   ┌────────────────────────────────┐
                   │   Emitters / Mock APIs         │
                   │  - NSX Policy API (FastAPI)    │
                   │  - NX-API (FastAPI)            │
                   │  - gNMI (WebSocket)            │
                   │  - Syslog (UDP / file)         │
                   │  - JSONL archive (always on)   │
                   └────────────────────────────────┘
```

## Two integration modes

**Mode A — Replay from JSONL** (best for development and CI):
- Run a scenario once. Archive lives in `runs/`.
- Your RCA engine reads the JSONL via `netops_sim.replay`.
- Deterministic, fast, no network.

**Mode B — Live API mocks** (best for integration tests and demos):
- `make mocks` spins up FastAPI servers on localhost.
- Your real NSX collector points at `http://localhost:8443` and never knows it's a mock.
- Validates the full collection path.

## Project layout

```
netsimu/
├── netops_sim/
│   ├── clock.py          # Discrete-event virtual clock
│   ├── topology.py       # Graph + reference topology builder
│   ├── entities.py       # State machines per entity type
│   ├── bus.py            # In-memory pub/sub
│   ├── physics.py        # Fault propagation (DFW-aware)
│   ├── faults.py         # Fault injection primitives
│   ├── distractors.py    # Background noise generator
│   ├── snapshots.py      # Periodic topology dumps + as-of materialization
│   ├── vmotion.py        # VM-to-host edge mutation
│   ├── scenarios.py      # 6 built-in scenarios
│   ├── runner.py         # Main loop, CLI
│   ├── replay.py         # JSONL replay harness
│   ├── grading.py        # Score RCA output vs ground truth
│   └── emitters/
│       ├── nsx_api.py    # NSX Policy API mock (FastAPI)
│       ├── nxapi.py      # Cisco NX-API mock (FastAPI)
│       ├── gnmi_ws.py    # gNMI WebSocket mock
│       ├── syslog.py     # Syslog UDP/file emitter
│       └── serve_all.py  # Run all mocks together
├── tests/                # 28 tests, all passing in <1s
├── scripts/
├── docs/
├── runs/                 # scenario outputs (gitignored)
├── pyproject.toml
├── Makefile
└── README.md
```

## Status

MVP-2 — six scenarios, distractor noise, topology snapshots, vMotion, DFW physics. **28 tests passing in <1s.**

Roadmap:
- Bayesian RCA engine (separate repo, consumes JSONL via replay)
- More scenarios: vMotion storms, asymmetric routing, MAC flapping, BFD timeout
- Time-versioned topology snapshots with delta encoding for scale
- GNN training-data export tooling
- Real-time visualization frontend

## License

TBD — internal mandnArgiTech project.
