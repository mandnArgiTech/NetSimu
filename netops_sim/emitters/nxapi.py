"""Cisco NX-API mock — JSON-RPC POST → CLI output.

Real NX-API is a POST to /ins with JSON-RPC payload. We accept the same
shape and fabricate reasonable outputs from current topology state.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from ..entities import BEHAVIORS, instantiate_behaviors
from ..topology import Topology, build_reference_topology

app = FastAPI(title="Cisco NX-API (mock)", version="0.1.0")
_TOPO: Topology = build_reference_topology()
# Standalone-mode bootstrap: ensure BEHAVIORS exist so we can return realistic
# counters even when no runner is alive. The runner re-instantiates anyway.
if not BEHAVIORS:
    instantiate_behaviors(_TOPO)


def _show_interface(host_filter: str | None = None) -> dict[str, Any]:
    from ..entities import BEHAVIORS, SwitchPortBehavior

    rows = []
    for e in _TOPO.by_type("switch_port"):
        if e.vendor != "cisco":
            continue
        parent = e.attrs.get("parent", "")
        if host_filter and parent != host_filter:
            continue
        beh = BEHAVIORS.get(e.id)
        if not isinstance(beh, SwitchPortBehavior):
            continue
        rows.append({
            "interface": e.id,
            "state": "up" if beh.s.oper_up else "down",
            "admin_state": "up" if beh.s.admin_up else "down",
            "mtu": beh.s.mtu,
            "speed": f"{beh.s.speed_gbps}G",
            "in_octets": beh.s.in_octets,
            "out_octets": beh.s.out_octets,
            "in_errors": beh.s.in_errors,
            "in_discards": beh.s.in_discards,
            "crc_errors": beh.s.crc_errors,
        })
    return {"TABLE_interface": {"ROW_interface": rows}}


def _show_bgp_summary() -> dict[str, Any]:
    from ..entities import BEHAVIORS, BGPBehavior

    rows = []
    for s in _TOPO.by_type("bgp_session"):
        beh = BEHAVIORS.get(s.id)
        state = beh.s.state if isinstance(beh, BGPBehavior) else "Established"
        rows.append({
            "neighbor": s.attrs.get("remote_ip", ""),
            "remote_as": s.attrs.get("remote_asn"),
            "state": state,
            "prefixes_received": beh.s.prefixes_received if isinstance(beh, BGPBehavior) else 50,
        })
    return {"TABLE_neighbor": {"ROW_neighbor": rows}}


def _show_running_diff() -> dict[str, Any]:
    from .. import audit_buffer

    return {"diffs": audit_buffer.recent()}


@app.post("/ins")
def nxapi_ins(payload: dict[str, Any]):
    """Accept any JSON-RPC NX-API payload, dispatch on the input string."""
    try:
        cmd = (payload.get("ins_api") or {}).get("input", "").strip().lower()
    except (AttributeError, TypeError):
        cmd = ""

    if cmd.startswith("show interface counters"):
        body = _show_interface()
    elif cmd.startswith("show interface"):
        body = _show_interface()
    elif cmd.startswith("show ip bgp summary"):
        body = _show_bgp_summary()
    elif cmd.startswith("show running-config diff"):
        body = _show_running_diff()
    elif cmd.startswith("show version"):
        body = {"version": "10.3(4)", "platform": "N9K-C93180YC-FX"}
    else:
        body = {"msg": f"unsupported in mock: {cmd!r}"}

    return {
        "ins_api": {
            "outputs": {
                "output": {"body": body, "code": "200", "msg": "Success"}
            }
        }
    }


@app.get("/healthz")
def health():
    return {"ok": True}
