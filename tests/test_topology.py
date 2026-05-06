from netops_sim.topology import build_reference_topology


def test_reference_topology_has_expected_components():
    t = build_reference_topology()
    s = t.stats()
    assert s["switch"] >= 6   # 2 spines + 4 ToRs
    assert s["esx_host"] == 8
    assert s["pnic"] == 16    # 8 hosts × 2 NICs
    assert s["tep"] == 8
    assert s["bgp_session"] == 2
    assert s["vpc"] == 3
    assert s["application"] == 3
    assert s["vm"] == 7
    assert s["dfw_rule"] == 3


def test_dual_homing_each_host_has_two_pnics():
    t = build_reference_topology()
    for host in t.by_type("esx_host"):
        pnics = list(t.neighbors(host.id, "has_pnic"))
        assert len(pnics) == 2, f"{host.id} should have 2 pNICs, got {len(pnics)}"


def test_tep_pair_full_mesh_for_prod_cluster():
    t = build_reference_topology()
    prod_hosts = [h.id for h in t.by_type("esx_host")
                  if h.attrs["cluster"] == "cluster-prod"]
    n = len(prod_hosts)
    expected_pairs = n * (n - 1) // 2
    actual_pairs = len(t.by_type("tep_pair"))
    assert actual_pairs == expected_pairs


def test_app_dependency_chain():
    t = build_reference_topology()
    web_deps = list(t.neighbors("app-web", "depends_on"))
    api_deps = list(t.neighbors("app-api", "depends_on"))
    assert "app-api" in web_deps
    assert "app-db" in api_deps


def test_path_exists_from_vm_to_tor():
    """A VM should be reachable to a ToR via the directed edges.

    Path is: VM → host → pNIC → ToR-host-port → ToR-spine-port → ToR-spine-port
    Need to traverse 'connects_to' edges and the inverse of 'has_port' (port belongs to switch).
    Use undirected projection for reachability."""
    import networkx as nx
    t = build_reference_topology()
    undirected = t.g.to_undirected()
    assert nx.has_path(undirected, "vm-web-01", "tor-01")
