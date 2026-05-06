"""vMotion-style helpers — move VMs between hosts at runtime.

In real VCF, vMotion fires when a host enters maintenance mode or fails.
HA orchestration picks a target host; the VM's RUNS_ON edge changes.
We model that here as an explicit graph mutation + bus event.
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bus import EventBus
    from .clock import VirtualClock
    from .topology import Topology


def vmotion(
    vm_id: str,
    new_host: str,
    topo: "Topology",
    bus: "EventBus",
    clock: "VirtualClock",
    reason: str = "ha_failover",
) -> bool:
    """Move VM to new_host. Updates the graph and emits a vmotion event.

    Returns True if successful. Returns False if VM/host don't exist or
    the graph already has VM on new_host.
    """
    if vm_id not in topo.entities or new_host not in topo.entities:
        return False

    old_hosts = list(topo.neighbors(vm_id, "runs_on"))
    if new_host in old_hosts:
        return False

    # Remove all existing runs_on edges
    for old in old_hosts:
        for k in list(topo.g[vm_id][old]):
            if k == "runs_on":
                topo.g.remove_edge(vm_id, old, key="runs_on")
                break

    # Add new runs_on
    topo.link(vm_id, new_host, "runs_on")

    # Emit a vCenter-style event
    bus.publish({
        "ts": clock.now_ts(),
        "source": "vcenter_event",
        "kind": "vmotion",
        "entity": vm_id,
        "from_host": old_hosts[0] if old_hosts else None,
        "to_host": new_host,
        "reason": reason,
    })
    bus.publish({
        "ts": clock.now_ts(),
        "source": "vcenter_event",
        "kind": "vm_runs_on_change",
        "entity": vm_id,
        "host": new_host,
    })
    return True


def evacuate_host(
    host_id: str,
    topo: "Topology",
    bus: "EventBus",
    clock: "VirtualClock",
    reason: str = "ha_failover",
) -> list[tuple[str, str]]:
    """Move all VMs off host_id to other hosts in the same cluster.

    Returns a list of (vm, new_host) pairs that were moved.
    """
    if host_id not in topo.entities:
        return []
    cluster = topo.entities[host_id].attrs.get("cluster")
    candidates = [
        h.id for h in topo.by_type("esx_host")
        if h.attrs.get("cluster") == cluster and h.id != host_id
    ]
    if not candidates:
        return []

    # Find VMs running on this host
    vms = list(topo.predecessors(host_id, "runs_on"))
    moves: list[tuple[str, str]] = []
    rng = random.Random(hash(host_id) & 0xFFFF)
    for vm in vms:
        target = rng.choice(candidates)
        if vmotion(vm, target, topo, bus, clock, reason=reason):
            moves.append((vm, target))
    return moves
