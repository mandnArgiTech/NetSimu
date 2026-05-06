"""Cross-entity fault propagation and application-impact synthesis.

Most propagation is *implicit* — TEPBehavior.tick() walks to its underlay path
and decides if it's healthy. But some signals (synthetic app probes, end-to-end
reachability) need an external orchestrator. That's what lives here.

Discipline: this file must not contain any logic that the RCA engine could
copy. We model the WORLD here (data path between VMs is broken → app sees
high latency). The RCA engine separately INFERS that from telemetry.
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bus import EventBus
    from .clock import VirtualClock
    from .topology import Topology


def app_impact_tick(clock: "VirtualClock", topo: "Topology", bus: "EventBus") -> None:
    """For each application dependency, sample one VM pair and emit the
    app-layer signal that monitoring tooling would observe."""
    apps = topo.by_type("application")
    for app in apps:
        deps = list(topo.neighbors(app.id, "depends_on"))
        if not deps:
            continue
        for dep in deps:
            vms_a = list(topo.neighbors(app.id, "consists_of"))
            vms_b = list(topo.neighbors(dep, "consists_of"))
            if not (vms_a and vms_b):
                continue

            # Determine the dependency port (used for DFW evaluation)
            dep_port: int | None = None
            for _, dst, k, data in topo.g.edges(app.id, keys=True, data=True):
                if dst == dep and k == "depends_on":
                    dep_port = data.get("port")
                    break

            healthy = _vm_to_vm_healthy(vms_a[0], vms_b[0], topo, dep_port)
            if not healthy:
                p99 = random.uniform(800, 2500)
                err5xx = random.uniform(0.05, 0.30)
            else:
                p99 = random.uniform(20, 80)
                err5xx = random.uniform(0.0, 0.005)

            bus.publish({
                "ts": clock.now_ts(),
                "source": "synthetic_probe",
                "kind": "app_health",
                "entity": app.id,
                "depends_on": dep,
                "metric": "p99_latency_ms",
                "value": round(p99, 2),
            })
            bus.publish({
                "ts": clock.now_ts(),
                "source": "app_logs",
                "kind": "http_metric",
                "entity": app.id,
                "metric": "5xx_rate",
                "value": round(err5xx, 4),
            })


def _vm_to_vm_healthy(
    vm_a: str, vm_b: str, topo: "Topology", port: int | None = None
) -> bool:
    """Trace the actual data path: VM-A → host → pNIC → port → ... → VM-B.

    Returns False if any of:
      - Underlay path broken (port down, MTU too small, etc.)
      - TEP unhealthy (e.g. duplicate IP)
      - DFW rule denies the flow on the given port
    """
    from .entities import BEHAVIORS, PNICBehavior, SwitchPortBehavior, TEPBehavior

    # ── DFW evaluation (new) ────────────────────────────────────────────
    # Pull the segment of each VM, evaluate DFW rules in priority order.
    seg_a = next(topo.neighbors(vm_a, "attached_to"), None)
    seg_b = next(topo.neighbors(vm_b, "attached_to"), None)
    if seg_a is not None and seg_b is not None:
        rules = sorted(
            topo.by_type("dfw_rule"),
            key=lambda r: r.attrs.get("priority", 9999),
        )
        for r in rules:
            r_src = r.attrs.get("src")
            r_dst = r.attrs.get("dst")
            r_port = r.attrs.get("port")
            r_action = r.attrs.get("action", "allow")
            if r.state.get("disabled"):
                continue
            if (r_src in ("any", seg_a)) and (r_dst in ("any", seg_b)):
                if r_port == "any" or (port is not None and r_port == port):
                    if r_action == "deny":
                        return False
                    break  # first allow wins, stop evaluating

    # ── Underlay/overlay path check ─────────────────────────────────────
    host_a = next(topo.neighbors(vm_a, "runs_on"), None)
    host_b = next(topo.neighbors(vm_b, "runs_on"), None)
    if host_a is None or host_b is None:
        return False
    if host_a == host_b:
        return True  # same host — no overlay encap needed

    for host in (host_a, host_b):
        tep_id = next(topo.neighbors(host, "has_tep"), None)
        if tep_id is None:
            return False
        tep_beh = BEHAVIORS.get(tep_id)
        if isinstance(tep_beh, TEPBehavior):
            if tep_beh.s.drop_rate_pps > 100:
                return False
            if topo.entities[tep_id].state.get("fault") == "ip_collision":
                return False

        any_healthy = False
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
                        any_healthy = True
                        break
            if any_healthy:
                break
        if not any_healthy:
            return False
    return True
