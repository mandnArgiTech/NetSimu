"""Built-in fault scenarios.

Each scenario is an async function: (clock, topo, bus) → ground_truth dict.
Ground truth is what the RCA engine must rediscover.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from . import audit_buffer
from .faults import emit_config_change, inject_fault

if TYPE_CHECKING:
    from .bus import EventBus
    from .clock import VirtualClock
    from .topology import Topology


async def _wait(clock: "VirtualClock", seconds: float) -> None:
    """Yield control until `seconds` of simulated time elapse."""
    fut: asyncio.Future = asyncio.get_event_loop().create_future()

    def resolve():
        if not fut.done():
            fut.set_result(None)

    clock.schedule(seconds, resolve)
    await fut


# ───────────────────────────────────────────────────────────────────────────
# Scenario 1 — MTU mismatch on a host-facing ToR port
# ───────────────────────────────────────────────────────────────────────────
async def scenario_mtu_mismatch(
    clock: "VirtualClock", topo: "Topology", bus: "EventBus"
) -> dict[str, Any]:
    """ToR host-facing port MTU 9216 → 1500. Geneve drops, app cascade.
    
    The change is applied via Ansible playbook 'standardize-mtu.yml' which
    affects both ToR uplinks the host is bonded to (realistic — playbooks
    rarely target a single port). This makes the cascade observable end-to-end.
    """
    # Both host-01 uplinks (LAG-equivalent) get the bad MTU
    targets = [
        "port-tor-01-host-01-vmnic0",
        "port-tor-03-host-01-vmnic1",
    ]
    primary = targets[0]

    await _wait(clock, 120)  # baseline window

    fault_t = clock.now()
    audit_buffer.append({
        "ts": clock.now_ts(),
        "user": "netadmin@corp",
        "device": "tor-01,tor-03",
        "change_id": "CHG-9281",
        "diff": {f"interface {t}": {"mtu": [9216, 1500]} for t in targets},
        "source": "ansible:standardize-mtu.yml",
    })
    for t in targets:
        emit_config_change(
            bus, clock, target=t,
            user="netadmin@corp", change_id="CHG-9281",
            diff={"interface": {"mtu": [9216, 1500]}},
            source="ansible:standardize-mtu.yml",
            state_changes={"mtu": 1500},
        )
        inject_fault(bus, clock, target=t,
                     fault_type="mtu_mismatch", drop_pps=8000)

    await _wait(clock, 240)

    return {
        "scenario": "mtu_mismatch",
        "fault_time": fault_t.isoformat(),
        "root_cause_entity": primary,
        "all_faulted_entities": targets,
        "expected_anomalies": [
            {"entity": primary, "metric": "in_errors"},
            {"entity_pattern": "teppair-host-01-*", "metric": "drop_pps"},
            {"entity": "tep-host-01", "metric": "encap_errors"},
            {"entity": "app-web", "metric": "p99_latency_ms"},
            {"entity": "app-web", "metric": "5xx_rate"},
        ],
        "expected_rca_rule": "R-MTU-001",
        "difficulty": "easy",
    }


# ───────────────────────────────────────────────────────────────────────────
# Scenario 2 — BGP session flap on T0
# ───────────────────────────────────────────────────────────────────────────
async def scenario_bgp_flap(
    clock: "VirtualClock", topo: "Topology", bus: "EventBus"
) -> dict[str, Any]:
    """T0 ↔ ToR BGP neighbor goes Idle for 45s, then re-establishes."""
    target = "bgp-t0-tor-01"

    await _wait(clock, 120)
    fault_t = clock.now()
    inject_fault(bus, clock, target=target,
                 fault_type="bgp_flap", duration=45)

    await _wait(clock, 240)

    return {
        "scenario": "bgp_flap",
        "fault_time": fault_t.isoformat(),
        "root_cause_entity": target,
        "expected_anomalies": [
            {"entity": target, "metric": "state"},
            {"entity": "t0-prod", "metric": "prefixes_received"},
        ],
        "expected_rca_rule": "R-BGP-001",
        "difficulty": "medium",
    }


# ───────────────────────────────────────────────────────────────────────────
# Scenario 3 — Silent packet loss on spine-tor link
# ───────────────────────────────────────────────────────────────────────────
async def scenario_silent_packet_loss(
    clock: "VirtualClock", topo: "Topology", bus: "EventBus"
) -> dict[str, Any]:
    """Subtle CRC corruption on spine-tor link. No link-down, ~150 pps drops."""
    target = "port-spine-01-to-tor-01"

    await _wait(clock, 120)
    fault_t = clock.now()
    inject_fault(bus, clock, target=target,
                 fault_type="crc_corruption", drop_pps=150)

    await _wait(clock, 480)

    return {
        "scenario": "silent_packet_loss",
        "fault_time": fault_t.isoformat(),
        "root_cause_entity": target,
        "expected_anomalies": [
            {"entity": target, "metric": "crc_errors"},
        ],
        "expected_rca_rule": "R-CRC-001",
        "difficulty": "hard",
    }


# ───────────────────────────────────────────────────────────────────────────
# Scenario 4 — TEP IP collision after host re-add
# ───────────────────────────────────────────────────────────────────────────
async def scenario_tep_ip_collision(
    clock: "VirtualClock", topo: "Topology", bus: "EventBus"
) -> dict[str, Any]:
    """Host re-added to NSX with stale TEP IP, colliding with an active TEP.

    Symptoms: duplicate-IP syslog, intermittent overlay drops, app cascade.
    Notably, no underlay errors — the underlay looks pristine.
    """
    target = "tep-host-02"  # the TEP that ends up colliding

    await _wait(clock, 120)
    fault_t = clock.now()

    audit_buffer.append({
        "ts": clock.now_ts(),
        "user": "vcfadmin@corp",
        "device": "nsx-manager",
        "change_id": "CHG-9402",
        "diff": {
            "transport_node host-02": {
                "tep_ip": ["10.20.0.12", "10.20.0.11"]   # stale → collides
            }
        },
        "source": "manual_recommission",
    })
    bus.publish({
        "kind": "audit_log",
        "ts": clock.now_ts(),
        "user": "vcfadmin@corp",
        "change_id": "CHG-9402",
        "target": target,
        "diff": {"tep_ip": ["10.20.0.12", "10.20.0.11"]},
        "source": "manual_recommission",
    })
    inject_fault(bus, clock, target=target, fault_type="ip_collision")

    await _wait(clock, 240)

    return {
        "scenario": "tep_ip_collision",
        "fault_time": fault_t.isoformat(),
        "root_cause_entity": target,
        "expected_anomalies": [
            {"entity": target, "metric": "encap_errors"},
            {"entity_pattern": "teppair-host-02-*", "metric": "drop_pps"},
            {"entity": "app-web", "metric": "p99_latency_ms"},
        ],
        "expected_rca_rule": "R-TEP-DUP-001",
        "expected_signals": [
            "syslog contains 'NSX-VTEP-3-DUP_IP'",
            "no underlay interface errors on host-02 ports",
        ],
        "difficulty": "medium",
    }


# ───────────────────────────────────────────────────────────────────────────
# Scenario 5 — DFW rule misconfiguration breaks app tier
# ───────────────────────────────────────────────────────────────────────────
async def scenario_dfw_rule_break(
    clock: "VirtualClock", topo: "Topology", bus: "EventBus"
) -> dict[str, Any]:
    """A DFW rule is changed from allow to deny, breaking web → api connectivity.

    The challenge for RCA: underlay/overlay are perfectly healthy. Only a
    config diff and app-layer signals point at this. Rule audit is critical.
    """
    target = "dfw-rule-001"  # web → api allow, will be flipped to deny
    rule_entity = topo.entities[target]

    await _wait(clock, 120)
    fault_t = clock.now()

    # Mutate the DFW rule directly — this changes physics
    rule_entity.attrs["action"] = "deny"

    audit_buffer.append({
        "ts": clock.now_ts(),
        "user": "secops@corp",
        "device": "nsx-manager",
        "change_id": "CHG-9510",
        "diff": {
            f"dfw_rule {target}": {
                "action": ["allow", "deny"],
                "display_name": ["web → api allow", "web → api allow"],  # forgot to rename
            }
        },
        "source": "compliance:zero-trust-rollout",
    })
    bus.publish({
        "kind": "audit_log",
        "ts": clock.now_ts(),
        "user": "secops@corp",
        "change_id": "CHG-9510",
        "target": target,
        "diff": {"action": ["allow", "deny"]},
        "source": "compliance:zero-trust-rollout",
    })
    bus.publish({
        "kind": "config_change",
        "ts": clock.now_ts(),
        "target": target,
        "changes": {"action": "deny"},
    })
    bus.publish({
        "ts": clock.now_ts(),
        "source": "syslog",
        "kind": "syslog",
        "entity": target,
        "severity": "warning",
        "msg": (
            f"NSX-DFW-4-RULE_CHANGE: rule {target} action changed "
            f"allow→deny by secops@corp (CHG-9510)"
        ),
    })

    await _wait(clock, 240)

    return {
        "scenario": "dfw_rule_break",
        "fault_time": fault_t.isoformat(),
        "root_cause_entity": target,
        "expected_anomalies": [
            {"entity": "app-web", "metric": "p99_latency_ms"},
            {"entity": "app-web", "metric": "5xx_rate"},
        ],
        "expected_rca_rule": "R-DFW-001",
        "expected_signals": [
            "no underlay errors",
            "no TEP drops",
            "audit log shows action allow → deny",
        ],
        "difficulty": "hard",
    }


# ───────────────────────────────────────────────────────────────────────────
# Scenario 6 — pNIC failure with vMotion cascade
# ───────────────────────────────────────────────────────────────────────────
async def scenario_pnic_failure_vmotion(
    clock: "VirtualClock", topo: "Topology", bus: "EventBus"
) -> dict[str, Any]:
    """Both pNICs on host-03 fail. HA evacuates VMs to host-01/host-04.

    Signals: pNIC link down, then vMotion events, then transient app blip
    until VMs settle. Topology *changes shape* mid-incident — exactly the
    case that breaks RCA tools without time-versioned graphs.
    """
    failed_host = "host-03"
    pnics = [f"pnic-{failed_host}-vmnic0", f"pnic-{failed_host}-vmnic1"]

    await _wait(clock, 120)
    fault_t = clock.now()

    # Both pNICs go down
    for pnic in pnics:
        inject_fault(bus, clock, target=pnic, fault_type="pnic_down")
        bus.publish({
            "ts": clock.now_ts(),
            "source": "syslog",
            "kind": "syslog",
            "entity": pnic,
            "severity": "critical",
            "msg": f"VMNIC-1-LINK_DOWN: {pnic} link state changed to down",
        })

    # Brief delay then HA reacts
    await _wait(clock, 30)

    # Evacuate the host
    from .vmotion import evacuate_host
    moves = evacuate_host(failed_host, topo, bus, clock, reason="ha_isolation")

    bus.publish({
        "ts": clock.now_ts(),
        "source": "vcenter_event",
        "kind": "ha_event",
        "entity": failed_host,
        "event": "host_isolated",
        "moved_vms": [vm for vm, _ in moves],
    })

    await _wait(clock, 210)

    return {
        "scenario": "pnic_failure_vmotion",
        "fault_time": fault_t.isoformat(),
        "root_cause_entity": pnics[0],
        "all_faulted_entities": pnics,
        "evacuated_vms": [vm for vm, _ in moves],
        "expected_anomalies": [
            {"entity": pnics[0], "metric": "link_up"},
            {"entity": pnics[1], "metric": "link_up"},
            {"entity_pattern": "vm-*", "metric": "vmotion"},
        ],
        "expected_rca_rule": "R-PNIC-DUAL-FAIL-001",
        "expected_signals": [
            "syslog VMNIC-1-LINK_DOWN on both pNICs of host-03",
            "vMotion events for VMs originally on host-03",
            "transient app latency that recovers post-vmotion",
        ],
        "difficulty": "medium",
    }


SCENARIOS = {
    "mtu_mismatch": scenario_mtu_mismatch,
    "bgp_flap": scenario_bgp_flap,
    "silent_packet_loss": scenario_silent_packet_loss,
    "tep_ip_collision": scenario_tep_ip_collision,
    "dfw_rule_break": scenario_dfw_rule_break,
    "pnic_failure_vmotion": scenario_pnic_failure_vmotion,
}
