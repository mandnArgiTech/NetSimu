"""Fault injection primitives — small helpers used by scenarios."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bus import EventBus
    from .clock import VirtualClock


def inject_fault(
    bus: "EventBus",
    clock: "VirtualClock",
    target: str,
    fault_type: str,
    **kwargs,
) -> None:
    """Publish a fault_inject event to the bus. The target's behavior reacts."""
    bus.publish({
        "kind": "fault_inject",
        "ts": clock.now_ts(),
        "target": target,
        "fault_type": fault_type,
        "clock": clock,
        **kwargs,
    })


def clear_fault(bus: "EventBus", clock: "VirtualClock", target: str) -> None:
    bus.publish({
        "kind": "fault_clear",
        "ts": clock.now_ts(),
        "target": target,
    })


def emit_config_change(
    bus: "EventBus",
    clock: "VirtualClock",
    target: str,
    user: str,
    change_id: str,
    diff: dict,
    source: str = "manual",
    state_changes: dict | None = None,
) -> None:
    """Emit both an audit-log event AND a state-mutating config_change event."""
    bus.publish({
        "kind": "audit_log",
        "ts": clock.now_ts(),
        "user": user,
        "change_id": change_id,
        "target": target,
        "diff": diff,
        "source": source,
    })
    if state_changes:
        bus.publish({
            "kind": "config_change",
            "ts": clock.now_ts(),
            "target": target,
            "changes": state_changes,
        })
