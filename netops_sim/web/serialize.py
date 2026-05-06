"""Topology → JSON serializer for the visual lab.

The frontend Cytoscape canvas consumes the shape produced here. We keep the
shape boring on purpose: a flat list of nodes and a flat list of edges, each
with the fields a renderer needs (id, type, layer, vendor, label, attrs)
plus enough relational info to draw labelled connections.

This is intentionally separate from snapshots.py — that one is for replay /
diff, this one is for human-facing rendering. They will diverge.
"""
from __future__ import annotations

from typing import Any

from ..topology import Topology

# Friendly display labels per type. Falls back to the raw id if absent.
_TYPE_LABELS: dict[str, str] = {
    "switch": "Switch",
    "switch_port": "Port",
    "esx_host": "ESX Host",
    "pnic": "pNIC",
    "tep": "TEP",
    "tep_pair": "TEP Pair",
    "nsx_edge": "NSX Edge",
    "tier0": "Tier-0 Gateway",
    "bgp_session": "BGP Session",
    "nsx_project": "NSX Project",
    "transit_gateway": "Transit Gateway",
    "vpc": "VPC",
    "segment": "Segment",
    "vm": "Virtual Machine",
    "application": "Application",
    "dfw_rule": "DFW Rule",
}


def _node_label(eid: str, etype: str, attrs: dict[str, Any]) -> str:
    """Human-friendly label shown under each node on the canvas."""
    if etype == "switch":
        role = attrs.get("role", "switch")
        model = attrs.get("model", "")
        return f"{eid}\n{role} · {model}" if model else eid
    if etype == "esx_host":
        cluster = attrs.get("cluster", "")
        return f"{eid}\n{cluster}" if cluster else eid
    if etype == "tep":
        ip = attrs.get("ip", "")
        return f"{eid}\n{ip}" if ip else eid
    if etype == "vpc":
        cidr = attrs.get("cidr", "")
        return f"{eid}\n{cidr}" if cidr else eid
    if etype == "vm":
        app = attrs.get("app", "")
        return f"{eid}\n{app}" if app else eid
    if etype == "bgp_session":
        return f"{eid}\nASN {attrs.get('local_asn')}↔{attrs.get('remote_asn')}"
    if etype == "dfw_rule":
        return f"{eid}\n{attrs.get('display_name', '')}"
    return eid


def serialize_topology(topo: Topology) -> dict[str, Any]:
    """Return a {nodes, edges, stats} dict ready for JSON encoding."""
    nodes: list[dict[str, Any]] = []
    for eid, e in topo.entities.items():
        nodes.append({
            "id": eid,
            "type": e.type,
            "layer": e.layer,
            "vendor": e.vendor,
            "label": _node_label(eid, e.type, e.attrs),
            "type_label": _TYPE_LABELS.get(e.type, e.type),
            "attrs": e.attrs,
        })

    edges: list[dict[str, Any]] = []
    for src, dst, key, data in topo.g.edges(keys=True, data=True):
        edges.append({
            # Cytoscape needs unique edge ids; (src, dst, rel) is unique here.
            "id": f"{src}--{key}--{dst}",
            "source": src,
            "target": dst,
            "rel": key,
            "attrs": {k: v for k, v in data.items() if k != "rel"},
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": topo.stats(),
    }
