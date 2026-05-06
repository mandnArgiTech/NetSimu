"""Per-entity behavior state machines.

Each entity type that emits telemetry or reacts to faults has a Behavior class.
Behaviors are instantiated once per entity at startup and registered globally.
The runner ticks them on a fixed cadence; faults are delivered via on_event.

Note: the simulator's "physics" (how a fault on X manifests at Y) lives partly
here (on_event reactions) and partly in physics.py (cross-entity propagation).
This is *intentionally* separate from the RCA engine's rules — they must not
share code, otherwise testing the engine becomes a tautology.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .bus import EventBus
    from .clock import VirtualClock
    from .topology import Topology


# ─── Global behavior registry ───────────────────────────────────────────────
BEHAVIORS: dict[str, "Behavior"] = {}


class Behavior:
    """Base class for entity state machines."""

    def __init__(self, eid: str) -> None:
        self.eid = eid

    async def tick(self, clock: "VirtualClock", topo: "Topology", bus: "EventBus") -> None:
        """Called every TICK_SECONDS. Override to emit periodic telemetry."""

    def on_event(self, event: dict[str, Any], topo: "Topology", bus: "EventBus") -> None:
        """Called for every event on the bus. Override to react to faults/changes."""


# ───────────────────────────────────────────────────────────────────────────
# Switch port
# ───────────────────────────────────────────────────────────────────────────
@dataclass
class SwitchPortState:
    admin_up: bool = True
    oper_up: bool = True
    speed_gbps: int = 25
    mtu: int = 9216
    in_octets: int = 0
    out_octets: int = 0
    in_pkts: int = 0
    out_pkts: int = 0
    in_errors: int = 0
    in_discards: int = 0
    out_errors: int = 0
    crc_errors: int = 0
    last_change_ts: float = 0.0
    nominal_pps: float = 50_000.0
    drop_rate_pps: float = 0.0
    fault_type: str | None = None


class SwitchPortBehavior(Behavior):
    """Models a switch port: counters tick up, drops apply when faulted."""

    TICK_SECONDS = 10.0

    def __init__(self, eid: str) -> None:
        super().__init__(eid)
        self.s = SwitchPortState()

    async def tick(self, clock, topo, bus) -> None:
        e = topo.entities[self.eid]
        s = self.s
        if not s.oper_up:
            bus.publish({
                "ts": clock.now_ts(),
                "source": "snmp" if e.vendor == "cisco" else "gnmi",
                "kind": "interface_counters",
                "entity": self.eid,
                "vendor": e.vendor,
                "in_octets": s.in_octets, "out_octets": s.out_octets,
                "in_errors": s.in_errors, "in_discards": s.in_discards,
                "crc_errors": s.crc_errors,
                "oper_status": "down",
                "admin_status": "up" if s.admin_up else "down",
                "mtu": s.mtu,
            })
            return

        dt = self.TICK_SECONDS
        pkts = int(s.nominal_pps * dt * random.uniform(0.85, 1.15))
        bytes_ = pkts * random.randint(200, 1400)
        s.in_pkts += pkts
        s.out_pkts += int(pkts * 0.95)
        s.in_octets += bytes_
        s.out_octets += int(bytes_ * 0.95)

        if s.drop_rate_pps > 0:
            drops = int(s.drop_rate_pps * dt * random.uniform(0.85, 1.15))
            if s.fault_type == "mtu_mismatch":
                s.in_errors += drops
                s.in_discards += drops // 2
            elif s.fault_type == "crc_corruption":
                s.crc_errors += drops
                s.in_errors += drops
            else:
                s.in_discards += drops

        bus.publish({
            "ts": clock.now_ts(),
            "source": "snmp" if e.vendor == "cisco" else "gnmi",
            "kind": "interface_counters",
            "entity": self.eid,
            "vendor": e.vendor,
            "in_octets": s.in_octets, "out_octets": s.out_octets,
            "in_pkts": s.in_pkts, "out_pkts": s.out_pkts,
            "in_errors": s.in_errors, "in_discards": s.in_discards,
            "out_errors": s.out_errors, "crc_errors": s.crc_errors,
            "oper_status": "up", "admin_status": "up" if s.admin_up else "down",
            "mtu": s.mtu, "speed_gbps": s.speed_gbps,
        })

    def on_event(self, event, topo, bus) -> None:
        if event.get("target") != self.eid:
            return
        kind = event.get("kind")
        if kind == "fault_inject":
            self.s.drop_rate_pps = float(event.get("drop_pps", 0))
            self.s.fault_type = event.get("fault_type")
            self.s.last_change_ts = event["ts"]
            if event.get("fault_type") == "link_down":
                self.s.oper_up = False
            bus.publish({
                "ts": event["ts"],
                "source": "syslog",
                "kind": "syslog",
                "entity": self.eid,
                "severity": "warning",
                "msg": f"ETHPORT-3-IF_ERROR: {self.eid} fault={event.get('fault_type')}",
            })
        elif kind == "fault_clear":
            self.s.drop_rate_pps = 0.0
            self.s.fault_type = None
            self.s.oper_up = True
            self.s.last_change_ts = event["ts"]
        elif kind == "config_change":
            for k, v in event.get("changes", {}).items():
                if hasattr(self.s, k):
                    setattr(self.s, k, v)
            self.s.last_change_ts = event["ts"]


# ───────────────────────────────────────────────────────────────────────────
# pNIC (host-side; minimal, mostly mirrors connected switch port)
# ───────────────────────────────────────────────────────────────────────────
@dataclass
class PNICState:
    link_up: bool = True
    mtu: int = 9000
    drop_rate_pps: float = 0.0


class PNICBehavior(Behavior):
    TICK_SECONDS = 30.0

    def __init__(self, eid: str) -> None:
        super().__init__(eid)
        self.s = PNICState()

    async def tick(self, clock, topo, bus) -> None:
        bus.publish({
            "ts": clock.now_ts(),
            "source": "esx_host_api",
            "kind": "pnic_status",
            "entity": self.eid,
            "link_up": self.s.link_up,
            "mtu": self.s.mtu,
        })

    def on_event(self, event, topo, bus) -> None:
        if event.get("target") != self.eid:
            return
        if event.get("kind") == "fault_inject" and event.get("fault_type") == "pnic_down":
            self.s.link_up = False
        elif event.get("kind") == "fault_clear":
            self.s.link_up = True


# ───────────────────────────────────────────────────────────────────────────
# TEP — health derives from underlay path
# ───────────────────────────────────────────────────────────────────────────
@dataclass
class TEPState:
    healthy: bool = True
    drop_rate_pps: float = 0.0
    encap_errors: int = 0


class TEPBehavior(Behavior):
    TICK_SECONDS = 15.0

    def __init__(self, eid: str) -> None:
        super().__init__(eid)
        self.s = TEPState()

    async def tick(self, clock, topo, bus) -> None:
        # Find parent host
        host = next(topo.predecessors(self.eid, "has_tep"), None)
        if host is None:
            return

        # If IP-collided, emit duplicate-IP syslog and intermittent drops
        if topo.entities[self.eid].state.get("fault") == "ip_collision":
            self.s.drop_rate_pps = 3000.0
            self.s.healthy = False
            self.s.encap_errors += int(self.s.drop_rate_pps * self.TICK_SECONDS)
            # Periodically emit duplicate-IP detection syslog
            import random as _r
            if _r.random() < 0.4:
                bus.publish({
                    "ts": clock.now_ts(),
                    "source": "syslog",
                    "kind": "syslog",
                    "entity": self.eid,
                    "severity": "error",
                    "msg": (
                        f"NSX-VTEP-3-DUP_IP: Duplicate TEP IP {topo.entities[self.eid].attrs.get('ip')} "
                        f"detected for {self.eid}"
                    ),
                })
            bus.publish({
                "ts": clock.now_ts(),
                "source": "nsx_central_cli",
                "kind": "tep_status",
                "entity": self.eid,
                "healthy": False,
                "drop_pps": self.s.drop_rate_pps,
                "encap_errors": self.s.encap_errors,
                "fault_hint": "duplicate_ip",
            })
            self._emit_pair_status(topo, bus, clock)
            return

        underlay_ok = self._underlay_path_ok(host, topo)
        if not underlay_ok:
            self.s.drop_rate_pps = 5000.0
            self.s.encap_errors += int(self.s.drop_rate_pps * self.TICK_SECONDS)
            self.s.healthy = False
        else:
            self.s.drop_rate_pps = max(0.0, self.s.drop_rate_pps - 1000.0)
            self.s.healthy = self.s.drop_rate_pps < 100

        bus.publish({
            "ts": clock.now_ts(),
            "source": "nsx_central_cli",
            "kind": "tep_status",
            "entity": self.eid,
            "healthy": self.s.healthy,
            "drop_pps": self.s.drop_rate_pps,
            "encap_errors": self.s.encap_errors,
        })

        self._emit_pair_status(topo, bus, clock)

    def _emit_pair_status(self, topo, bus, clock) -> None:
        """Emit per-pair telemetry for any pair this TEP belongs to."""
        for pair in topo.neighbors(self.eid, "in_pair"):
            other_tep = next(
                (x for x in topo.predecessors(pair, "in_pair") if x != self.eid),
                None,
            )
            other_beh = BEHAVIORS.get(other_tep) if other_tep else None
            other_drop = other_beh.s.drop_rate_pps if isinstance(other_beh, TEPBehavior) else 0.0
            pair_drop = max(self.s.drop_rate_pps, other_drop)
            bus.publish({
                "ts": clock.now_ts(),
                "source": "nsx_intelligence",
                "kind": "tep_pair_status",
                "entity": pair,
                "drop_pps": pair_drop,
                "members": [self.eid, other_tep],
            })

    def _underlay_path_ok(self, host: str, topo) -> bool:
        for pnic in topo.neighbors(host, "has_pnic"):
            pnic_beh = BEHAVIORS.get(pnic)
            if isinstance(pnic_beh, PNICBehavior) and not pnic_beh.s.link_up:
                continue
            for tor_port in topo.neighbors(pnic, "connects_to"):
                port_beh = BEHAVIORS.get(tor_port)
                if isinstance(port_beh, SwitchPortBehavior):
                    if (port_beh.s.oper_up
                            and port_beh.s.drop_rate_pps < 100
                            and port_beh.s.mtu >= 1700):
                        return True
        return False

    def on_event(self, event, topo, bus) -> None:
        if event.get("target") != self.eid:
            return
        kind = event.get("kind")
        if kind == "fault_inject":
            ft = event.get("fault_type")
            topo.entities[self.eid].state["fault"] = ft
            if ft == "ip_collision":
                self.s.healthy = False
                self.s.drop_rate_pps = 3000.0
        elif kind == "fault_clear":
            topo.entities[self.eid].state.pop("fault", None)
            self.s.drop_rate_pps = 0.0
            self.s.healthy = True


# ───────────────────────────────────────────────────────────────────────────
# BGP session
# ───────────────────────────────────────────────────────────────────────────
@dataclass
class BGPState:
    state: str = "Established"  # Idle, Active, Established
    last_change_ts: float = 0.0
    flap_count: int = 0
    prefixes_received: int = 50


class BGPBehavior(Behavior):
    TICK_SECONDS = 30.0

    def __init__(self, eid: str) -> None:
        super().__init__(eid)
        self.s = BGPState()

    async def tick(self, clock, topo, bus) -> None:
        bus.publish({
            "ts": clock.now_ts(),
            "source": "gnmi",
            "kind": "bgp_neighbor",
            "entity": self.eid,
            "state": self.s.state,
            "prefixes": self.s.prefixes_received if self.s.state == "Established" else 0,
            "flap_count": self.s.flap_count,
        })

    def on_event(self, event, topo, bus) -> None:
        if event.get("target") != self.eid:
            return
        if event.get("kind") == "fault_inject" and event.get("fault_type") == "bgp_flap":
            old = self.s.state
            self.s.state = "Idle"
            self.s.flap_count += 1
            self.s.last_change_ts = event["ts"]
            bus.publish({
                "ts": event["ts"],
                "source": "syslog",
                "kind": "syslog",
                "entity": self.eid,
                "severity": "warning",
                "msg": f"BGP-5-ADJCHANGE: neighbor {self.eid} state {old} -> Idle",
            })
            duration = event.get("duration", 30)
            clock = event["clock"]

            def restore():
                self.s.state = "Established"
                self.s.last_change_ts = clock.now_ts()
                bus.publish({
                    "ts": clock.now_ts(),
                    "source": "syslog",
                    "kind": "syslog",
                    "entity": self.eid,
                    "severity": "info",
                    "msg": f"BGP-5-ADJCHANGE: neighbor {self.eid} state Idle -> Established",
                })

            clock.schedule(duration, restore)


# ───────────────────────────────────────────────────────────────────────────
# Dispatch table
# ───────────────────────────────────────────────────────────────────────────
BEHAVIOR_CLASSES: dict[str, type[Behavior]] = {
    "switch_port": SwitchPortBehavior,
    "pnic": PNICBehavior,
    "tep": TEPBehavior,
    "bgp_session": BGPBehavior,
}


def instantiate_behaviors(topo) -> None:
    """Create one behavior per matching entity, register globally."""
    BEHAVIORS.clear()
    for eid, e in topo.entities.items():
        cls = BEHAVIOR_CLASSES.get(e.type)
        if cls:
            BEHAVIORS[eid] = cls(eid)


def reset_behaviors() -> None:
    BEHAVIORS.clear()
