# Architecture

## Why a simulator at all

Building an RCA platform for VCF/NSX + multi-vendor underlay needs:

1. **Repeatable, labeled incidents** for training & evaluation.
2. **Realistic telemetry shapes** so collectors and parsers are exercised end-to-end.
3. **Cheap iteration** — a faulty RCA rule shouldn't require a customer outage to discover.

A real lab (vSphere + NSX + Cisco/Arista hardware) is none of these. Container labs (cEOS, Nexus 9000v) are closer but heavy and license-encumbered.

NetSimu trades faithfulness-of-control-plane for faithfulness-of-telemetry. We don't run real NX-OS — we generate the byte patterns NX-OS would emit. For an RCA platform, that's exactly the right boundary.

## Design principles

1. **One process, one event loop.** No microservices in the simulator. Determinism > scalability.
2. **Discrete-event clock.** Sim time is decoupled from wall time. 4 hours of operation in 30 ms.
3. **Behaviors over scripts.** Each entity owns its state machine. Faults mutate state; behaviors emit telemetry. No global "scripted timeline."
4. **Physics ≠ RCA rules.** The propagation rules in `physics.py` describe how the world reacts to faults. The RCA engine (separate codebase) infers from telemetry alone. They must never share code.
5. **Mocks expose real wire-shapes.** NSX Policy API mock answers the same JSON your real NSX answers. NX-API JSON-RPC, gNMI updates — same. So your collectors don't know they're talking to a mock.

## Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      Scenario (coroutine)                       │
│  Schedules: baseline → inject fault → wait → return ground-truth│
└──────────────────────────────┬──────────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
        ┌────────────────┐            ┌──────────────┐
        │ VirtualClock   │            │  EventBus    │
        │  - heap queue  │            │  - pub/sub   │
        │  - virt time   │            │  - in-mem    │
        └───────┬────────┘            └──────┬───────┘
                │                            │
                ▼                            │
        ┌────────────────┐                   │
        │ Behaviors      │  one per          │
        │  - SwitchPort  │  switch_port,     │
        │  - PNIC        │  pnic, tep,       │
        │  - TEP         │  bgp_session      │
        │  - BGP         │                   │
        │  tick + react  │───────────────────┘
        └────────┬───────┘
                 │ reads/writes
                 ▼
        ┌────────────────┐
        │ Topology       │  NetworkX MultiDiGraph
        │  100 entities  │  ~180 edges
        │  4 layers      │  per-entity .state dict
        └────────────────┘

        Subscribers fan out to:
          - JSONL archive sink (always on)
          - FastAPI mocks (NSX, NX-API)
          - WebSocket gNMI mock
          - Syslog file/UDP emitter
```

## Bitemporal context (forward compat)

The simulator does NOT track entity history — it only knows current state. Your RCA platform's persistent topology store *should* be bitemporal (valid_time + transaction_time). When a VM moves, the simulator just edits the graph in place; downstream collectors are responsible for emitting the move event so the persistent store can close one edge and open another.

This separation matters: the simulator's `Topology` is a *current view*, while a production RCA store needs an `as-of` query. Don't blur them.

## Choosing simulation depth

You'll often face a tradeoff: do I model X realistically, or do I cheat?

**Cheat when:**
- The RCA engine doesn't read X (e.g., LACP hash distribution — we don't model it; instead the scenarios fault both bonded links).
- The cheat is monotonic (e.g., we set `drop_pps` to a constant when faulted; reality has bursts, but the RCA engine treats it the same).

**Don't cheat when:**
- The cheat would change the RCA engine's correctness (e.g., we DO model dual-homing because RCA must distinguish "one uplink down" from "host isolated").
- The cheat would let the RCA engine cheat back (e.g., we don't directly emit "root cause is X" anywhere — only telemetry that would exist in the real world).

## Extending NetSimu

**New entity types** — add a Behavior subclass, wire it into `BEHAVIOR_CLASSES`, link entities in `build_reference_topology`.

**New scenarios** — add an async function to `scenarios.py`, register in `SCENARIOS`. Include ground truth.

**New telemetry source** — add an emitter under `netops_sim/emitters/`. Subscribe to bus events; format to vendor's wire shape.

**Larger topologies** — `build_reference_topology()` is parametrizable in spirit; add `build_topology(num_hosts=64, ...)` for scale tests. The simulator handles ~10k entities on a single core.

## What the simulator is *not*

- Not a control-plane simulator. It doesn't run BGP state machines or compute SPF; BGP state changes are stub events.
- Not a packet-level simulator. Counters are statistical, not flow-by-flow. (If you need flow-level, plug in a real ns-3 backend; it's a 1-week project.)
- Not a security testbed. There's no DFW evaluation, no IDS hooks. Add when needed.
