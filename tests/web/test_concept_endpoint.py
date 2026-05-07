"""Tests for the concept-content endpoints (M2)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from netops_sim.topology import build_reference_topology
from netops_sim.web.content_loader import list_concept_ids
from netops_sim.web.server import create_app


def _client() -> TestClient:
    return TestClient(create_app(topology=build_reference_topology()))


# Every entity type the topology renders needs a concept entry. tep_pair
# and bgp_session are hidden in M1 layout but must still be documented for
# when M2/M3 layout polish surfaces them.
_REQUIRED_ENTITY_CONCEPTS = {
    "spine",
    "tor",
    "switch_port",
    "esx_host",
    "pnic",
    "tep",
    "tep_pair",
    "nsx_edge",
    "tier0",
    "bgp_session",
    "nsx_project",
    "transit_gateway",
    "vpc",
    "segment",
    "vm",
    "application",
    "dfw_rule",
}

# Cross-link concepts referenced from entity-type pages.
_REQUIRED_CROSSLINK_CONCEPTS = {
    "geneve",
    "mtu",
    "bgp",
    "vlan",
    "vmotion",
    "dfw",
    "encapsulation",
}


def test_list_concepts_includes_all_required() -> None:
    res = _client().get("/api/concepts")
    assert res.status_code == 200
    ids = set(res.json()["ids"])
    missing = (_REQUIRED_ENTITY_CONCEPTS | _REQUIRED_CROSSLINK_CONCEPTS) - ids
    assert not missing, f"missing concept files: {sorted(missing)}"


def test_get_known_concept_returns_id_title_body() -> None:
    res = _client().get("/api/concept/tep")
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == "tep"
    assert body["title"] == "TEP (Tunnel Endpoint)"
    # Body has substantive content + cross-links.
    assert len(body["body"]) > 500
    assert "concept:geneve" in body["body"]


def test_get_unknown_concept_returns_404() -> None:
    res = _client().get("/api/concept/nonexistent_thing")
    assert res.status_code == 404


def test_concept_id_path_traversal_is_rejected() -> None:
    # The loader's id regex blocks anything containing slashes or dots.
    res = _client().get("/api/concept/..%2Fserver")
    # Either 404 (loader rejects), or 400/422 — both are fine; the
    # important thing is we don't 200 with file contents.
    assert res.status_code in {400, 404, 422}


def test_every_required_concept_resolves() -> None:
    """Smoke-load every required concept to catch malformed frontmatter."""
    client = _client()
    for cid in _REQUIRED_ENTITY_CONCEPTS | _REQUIRED_CROSSLINK_CONCEPTS:
        res = client.get(f"/api/concept/{cid}")
        assert res.status_code == 200, f"failed to load {cid}"
        body = res.json()
        assert body["title"], f"empty title for {cid}"
        assert body["body"], f"empty body for {cid}"


def test_loader_filesystem_listing_matches_endpoint() -> None:
    res = _client().get("/api/concepts")
    assert sorted(res.json()["ids"]) == list_concept_ids()
