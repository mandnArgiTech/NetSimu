"""NSX Policy API mock — answers a subset of /policy/api/v1/* used by collectors.

Run standalone:  uvicorn netops_sim.emitters.nsx_api:app --port 8443
Or via:          make mocks
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI, Query

from .. import audit_buffer
from ..entities import BEHAVIORS, instantiate_behaviors
from ..topology import Topology, build_reference_topology

app = FastAPI(title="NSX Policy API (mock)", version="0.1.0")
_TOPO: Topology = build_reference_topology()
if not BEHAVIORS:
    instantiate_behaviors(_TOPO)


def _entity_to_payload(eid: str) -> dict[str, Any]:
    e = _TOPO.entities[eid]
    return {
        "id": e.id,
        "display_name": e.id,
        "resource_type": e.type,
        "vendor": e.vendor,
        **e.attrs,
    }


@app.get("/policy/api/v1/orgs/default/projects")
def list_projects():
    projects = _TOPO.by_type("nsx_project")
    return {
        "results": [_entity_to_payload(p.id) for p in projects],
        "result_count": len(projects),
    }


@app.get("/policy/api/v1/search/query")
def search(query: str = Query(...)):
    """Approximation of the NSX search API. Supports `resource_type:<Type>`."""
    type_map = {
        "Vpc": "vpc", "VpcSubnet": "segment",
        "Segment": "segment", "Tier0": "tier0",
        "TransitGateway": "transit_gateway", "TransportNode": "esx_host",
    }
    parts = query.split(":")
    if len(parts) == 2 and parts[0].strip().lower() == "resource_type":
        target_type = type_map.get(parts[1].strip())
        if target_type is None:
            return {"results": [], "result_count": 0}
        items = _TOPO.by_type(target_type)
        return {
            "results": [_entity_to_payload(e.id) for e in items],
            "result_count": len(items),
        }
    return {"results": [], "result_count": 0}


@app.get("/policy/api/v1/infra/tier-0s")
def list_tier0s():
    items = _TOPO.by_type("tier0")
    return {"results": [_entity_to_payload(e.id) for e in items],
            "result_count": len(items)}


@app.get("/policy/api/v1/infra/tier-0s/{t0_id}/locale-services/default/bgp/neighbors/status")
def bgp_status(t0_id: str):
    from ..entities import BEHAVIORS, BGPBehavior

    sessions = _TOPO.by_type("bgp_session")
    out = []
    for s in sessions:
        beh = BEHAVIORS.get(s.id)
        state = beh.s.state if isinstance(beh, BGPBehavior) else "Established"
        out.append({
            "neighbor_address": s.attrs.get("remote_ip", ""),
            "connection_state": state,
            "remote_as_number": s.attrs.get("remote_asn"),
            "messages_received_count": 1234,
        })
    return {"results": out, "result_count": len(out)}


@app.get("/policy/api/v1/infra/transit-gateways")
def list_tgws():
    items = _TOPO.by_type("transit_gateway")
    return {"results": [_entity_to_payload(e.id) for e in items],
            "result_count": len(items)}


@app.get("/policy/api/v1/infra/audit-logs")
def get_audit_logs(since: str | None = None):
    since_ts: float | None = None
    if since:
        try:
            since_ts = datetime.fromisoformat(since.replace("Z", "+00:00")).timestamp()
        except ValueError:
            since_ts = None
    return {"results": audit_buffer.recent(since_ts)}


@app.get("/policy/api/v1/infra/realized-state/realized-entities")
def realized_state():
    """Stub: mark every overlay entity as REALIZED."""
    items = []
    for e in _TOPO.entities.values():
        if e.layer == "overlay":
            items.append({
                "id": e.id, "resource_type": e.type,
                "state": "REALIZED", "alarms": [],
            })
    return {"results": items, "result_count": len(items)}


@app.get("/api/v1/transport-nodes")
def list_transport_nodes():
    items = _TOPO.by_type("esx_host")
    return {
        "results": [{
            "id": e.id, "display_name": e.id,
            "node_deployment_info": {"ip_addresses": ["10.10.10.x"]},
            **e.attrs,
        } for e in items],
        "result_count": len(items),
    }


@app.get("/api/v1/transport-nodes/{tn_id}/tunnels")
def tunnel_status(tn_id: str):
    from ..entities import BEHAVIORS, TEPBehavior

    tep_id = f"tep-{tn_id}"
    beh = BEHAVIORS.get(tep_id)
    healthy = beh.s.healthy if isinstance(beh, TEPBehavior) else True
    return {"results": [{
        "remote_node_id": "host-other",
        "status": "UP" if healthy else "DOWN",
        "encap": "GENEVE",
    }]}


@app.get("/healthz")
def health():
    return {"ok": True, "topology_size": _TOPO.stats()}
