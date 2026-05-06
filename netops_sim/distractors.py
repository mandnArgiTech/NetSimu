"""Distractor noise generator — produces background anomalies unrelated to the
injected fault. Forces an RCA engine to discriminate true root cause from
coincidental noise.

Three flavors:
  - cpu_spike      on random ESX hosts (mimics scheduled jobs, GC)
  - disk_io        on random VMs (mimics backup/snapshot)
  - mem_pressure   on random hosts (mimics workload bursts)

Each spike has a random duration (30-180s) and severity. Spikes overlap with
the real fault window so the RCA engine cannot just "look at what spiked."
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bus import EventBus
    from .clock import VirtualClock
    from .topology import Topology


@dataclass
class DistractorConfig:
    """Tunable noise level."""
    rate_per_minute: float = 2.0    # how many distractor anomalies per sim minute
    cpu_prob: float = 0.4           # mix of distractor types
    disk_prob: float = 0.4
    mem_prob: float = 0.2
    min_duration: float = 30.0
    max_duration: float = 180.0
    seed: int | None = None


class DistractorNoiseGenerator:
    """Periodically schedules random spikes on random entities."""

    def __init__(
        self,
        config: DistractorConfig | None = None,
        excluded_entities: set[str] | None = None,
    ):
        self.config = config or DistractorConfig()
        # Entities to NEVER fire distractors on — typically the actual root
        # cause and its immediate neighbors. Scenarios populate this so we
        # don't accidentally make RCA easier or harder than intended.
        self.excluded = excluded_entities or set()
        self._rng = random.Random(self.config.seed)
        self._active_spikes: dict[str, float] = {}  # entity → end_ts

    def start(self, clock: "VirtualClock", topo: "Topology", bus: "EventBus") -> None:
        """Schedule the first generation tick. Self-perpetuating."""
        clock.schedule(0.5, lambda: self._tick(clock, topo, bus))

    def _tick(self, clock: "VirtualClock", topo: "Topology", bus: "EventBus") -> None:
        # Clean up expired spikes
        now = clock.now_ts()
        self._active_spikes = {
            ent: end for ent, end in self._active_spikes.items() if end > now
        }

        # Generate a distractor with probability proportional to rate
        # tick interval (sec) × rate_per_minute / 60
        tick_interval = 5.0
        p_spawn = (tick_interval * self.config.rate_per_minute) / 60.0
        if self._rng.random() < p_spawn:
            self._spawn_distractor(clock, topo, bus)

        # Re-schedule
        clock.schedule(tick_interval, lambda: self._tick(clock, topo, bus))

        # Continue emitting active spikes' telemetry every tick
        for ent, end_ts in self._active_spikes.items():
            self._emit_active_spike(ent, clock, bus)

    def _spawn_distractor(
        self, clock: "VirtualClock", topo: "Topology", bus: "EventBus"
    ) -> None:
        kind = self._rng.choices(
            ["cpu", "disk", "mem"],
            weights=[self.config.cpu_prob, self.config.disk_prob, self.config.mem_prob],
            k=1,
        )[0]

        if kind == "cpu" or kind == "mem":
            candidates = [
                e.id for e in topo.by_type("esx_host") if e.id not in self.excluded
            ]
        else:  # disk
            candidates = [
                e.id for e in topo.by_type("vm") if e.id not in self.excluded
            ]
        if not candidates:
            return

        entity = self._rng.choice(candidates)
        if entity in self._active_spikes:
            return  # already spiking, skip

        duration = self._rng.uniform(
            self.config.min_duration, self.config.max_duration
        )
        end_ts = clock.now_ts() + duration
        self._active_spikes[entity] = end_ts

        bus.publish({
            "ts": clock.now_ts(),
            "source": "distractor",
            "kind": "distractor_start",
            "entity": entity,
            "category": kind,
            "duration_s": round(duration, 1),
        })
        self._emit_active_spike(entity, clock, bus, kind=kind, intro=True)

    def _emit_active_spike(
        self,
        entity: str,
        clock: "VirtualClock",
        bus: "EventBus",
        kind: str | None = None,
        intro: bool = False,
    ) -> None:
        """Publish a single noisy datapoint."""
        # Determine kind from entity if not given (cpu/mem on hosts, disk on VMs)
        if kind is None:
            kind = "disk" if entity.startswith("vm-") else self._rng.choice(["cpu", "mem"])

        if kind == "cpu":
            value = round(self._rng.uniform(78, 99), 1)
            bus.publish({
                "ts": clock.now_ts(),
                "source": "esx_host_api",
                "kind": "host_metric",
                "entity": entity,
                "metric": "cpu_pct",
                "value": value,
            })
        elif kind == "mem":
            value = round(self._rng.uniform(82, 96), 1)
            bus.publish({
                "ts": clock.now_ts(),
                "source": "esx_host_api",
                "kind": "host_metric",
                "entity": entity,
                "metric": "mem_pct",
                "value": value,
            })
        else:  # disk
            value = round(self._rng.uniform(40, 220), 1)
            bus.publish({
                "ts": clock.now_ts(),
                "source": "vm_metric",
                "kind": "vm_metric",
                "entity": entity,
                "metric": "disk_io_latency_ms",
                "value": value,
            })


# ────────────────────────────────────────────────────────────────────────────
# Convenience helpers
# ────────────────────────────────────────────────────────────────────────────
def attach_distractors(
    clock: "VirtualClock",
    topo: "Topology",
    bus: "EventBus",
    excluded: set[str] | None = None,
    config: DistractorConfig | None = None,
) -> DistractorNoiseGenerator:
    """One-call attach. Use from a scenario or the runner."""
    gen = DistractorNoiseGenerator(config=config, excluded_entities=excluded)
    gen.start(clock, topo, bus)
    return gen
