"""M1 backend smoke test: /api/topology serves the reference topology.

What we assert:
  - Endpoint returns 200 with a JSON body shaped {nodes, edges, stats}.
  - Counts match the reference topology (103 nodes, 186 edges as of MVP-2).
  - Every node carries id, type, layer, vendor, label, attrs.
  - Every edge carries id, source, target, rel.
  - All four expected layers appear (physical, underlay, overlay, application).
  - Sample entities the frontend will render show up correctly typed.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from netops_sim.topology import build_reference_topology
from netops_sim.web.server import create_app


def _client() -> TestClient:
    return TestClient(create_app(topology=build_reference_topology()))


def test_health_endpoint() -> None:
    res = _client().get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_topology_endpoint_returns_full_reference_topology() -> None:
    res = _client().get("/api/topology")
    assert res.status_code == 200
    body = res.json()

    assert set(body.keys()) == {"nodes", "edges", "stats"}

    # Counts come from netops_sim.topology.build_reference_topology — if these
    # change because the topology grew, update the expected numbers AND the
    # design doc together (the "8 hosts / 4 ToRs / 2 spines" story matters).
    expected = build_reference_topology().stats()
    assert body["stats"] == expected
    assert len(body["nodes"]) == expected["nodes"]
    assert len(body["edges"]) == expected["edges"]


def test_every_node_has_required_fields() -> None:
    body = _client().get("/api/topology").json()
    required = {"id", "type", "layer", "vendor", "label", "type_label", "attrs"}
    for n in body["nodes"]:
        assert required.issubset(n.keys()), f"node missing fields: {n}"
        assert n["layer"] in {"physical", "underlay", "overlay", "application"}


def test_every_edge_has_required_fields() -> None:
    body = _client().get("/api/topology").json()
    required = {"id", "source", "target", "rel", "attrs"}
    edge_ids = set()
    for e in body["edges"]:
        assert required.issubset(e.keys()), f"edge missing fields: {e}"
        # Cytoscape needs unique edge ids.
        assert e["id"] not in edge_ids, f"duplicate edge id: {e['id']}"
        edge_ids.add(e["id"])


def test_all_four_layers_present() -> None:
    body = _client().get("/api/topology").json()
    layers = {n["layer"] for n in body["nodes"]}
    assert layers == {"physical", "underlay", "overlay", "application"}


def test_known_entities_serialized_correctly() -> None:
    body = _client().get("/api/topology").json()
    by_id = {n["id"]: n for n in body["nodes"]}

    # Sample one of each major type the frontend renders.
    assert by_id["spine-01"]["type"] == "switch"
    assert by_id["spine-01"]["layer"] == "underlay"
    assert by_id["spine-01"]["vendor"] == "arista"

    assert by_id["tor-01"]["vendor"] == "cisco"
    assert by_id["host-01"]["type"] == "esx_host"
    assert by_id["host-01"]["layer"] == "physical"
    assert by_id["tep-host-01"]["type"] == "tep"
    assert by_id["tep-host-01"]["layer"] == "overlay"
    assert "10.20.0" in by_id["tep-host-01"]["label"]  # IP shows on the chip
    assert by_id["t0-prod"]["type"] == "tier0"
    assert by_id["seg-web"]["type"] == "segment"
    assert by_id["vm-web-01"]["type"] == "vm"
    assert by_id["app-web"]["type"] == "application"
