"""Topology graph + reference topology builder.

The graph is in-memory NetworkX. It mirrors the production bitemporal Neo4j
schema but without history tracking — that's the collectors' job downstream.

The reference topology models a small, realistic VCF deployment:
  - 2 spines, 4 ToRs (mixed Cisco/Arista vendors)
  - 8 ESX hosts (3 clusters: prod / edge / mgmt)
  - dual-homed pNICs per host (vmnic0 → tor-A, vmnic1 → tor-B)
  - 1 NSX Tier-0, 1 Transit Gateway, 1 Project, 3 VPCs, 4 segments
  - BGP sessions T0 ↔ ToRs
  - 7 VMs across 3 application tiers (web / api / db)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

import networkx as nx


@dataclass
class Entity:
    """A node in the topology graph."""

    id: str
    type: str
    layer: str  # 'physical' | 'underlay' | 'overlay' | 'application'
    vendor: str = ""
    attrs: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)  # mutable, for fault flags

    def __repr__(self) -> str:
        return f"Entity({self.id}, {self.type})"


class Topology:
    def __init__(self) -> None:
        self.g: nx.MultiDiGraph = nx.MultiDiGraph()
        self.entities: dict[str, Entity] = {}

    def add(self, e: Entity) -> Entity:
        self.entities[e.id] = e
        self.g.add_node(e.id, entity=e)
        return e

    def link(self, src: str, dst: str, rel: str, **attrs: Any) -> None:
        if src not in self.entities or dst not in self.entities:
            raise KeyError(f"link: missing entity ({src} or {dst})")
        self.g.add_edge(src, dst, key=rel, rel=rel, **attrs)

    def neighbors(self, eid: str, rel: str | None = None) -> Iterator[str]:
        """Outgoing neighbors, optionally filtered by relationship name."""
        for _, dst, k in self.g.out_edges(eid, keys=True):
            if rel is None or k == rel:
                yield dst

    def predecessors(self, eid: str, rel: str | None = None) -> Iterator[str]:
        """Incoming neighbors, optionally filtered by relationship name."""
        for src, _, k in self.g.in_edges(eid, keys=True):
            if rel is None or k == rel:
                yield src

    def by_type(self, type_: str) -> list[Entity]:
        return [e for e in self.entities.values() if e.type == type_]

    def shortest_path(self, src: str, dst: str) -> list[str] | None:
        try:
            return nx.shortest_path(self.g, src, dst)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def stats(self) -> dict[str, int]:
        type_counts: dict[str, int] = {}
        for e in self.entities.values():
            type_counts[e.type] = type_counts.get(e.type, 0) + 1
        return {
            "nodes": self.g.number_of_nodes(),
            "edges": self.g.number_of_edges(),
            **type_counts,
        }


def build_reference_topology() -> Topology:
    """Construct the canonical 8-host / 4-ToR / 2-spine reference topology."""
    t = Topology()

    # ── Spines (Arista) ──────────────────────────────────────────────────
    for i in (1, 2):
        t.add(Entity(
            f"spine-{i:02d}", "switch", "underlay", "arista",
            attrs={"model": "DCS-7280SR3", "asn": 65000, "role": "spine"},
        ))

    # ── ToRs (mixed vendor) ──────────────────────────────────────────────
    tor_specs = [
        ("tor-01", "cisco", "N9K-C93180YC-FX", 65001, "rack-01"),
        ("tor-02", "cisco", "N9K-C93180YC-FX", 65001, "rack-01"),
        ("tor-03", "arista", "DCS-7050SX3", 65002, "rack-02"),
        ("tor-04", "arista", "DCS-7050SX3", 65002, "rack-02"),
    ]
    for tid, vendor, model, asn, rack in tor_specs:
        t.add(Entity(
            tid, "switch", "underlay", vendor,
            attrs={"model": model, "asn": asn, "rack": rack, "role": "tor"},
        ))

    # ── Spine ↔ ToR fabric links ─────────────────────────────────────────
    for spine in ("spine-01", "spine-02"):
        for tor in ("tor-01", "tor-02", "tor-03", "tor-04"):
            sp_port = f"port-{spine}-to-{tor}"
            tor_port = f"port-{tor}-to-{spine}"
            t.add(Entity(
                sp_port, "switch_port", "underlay", t.entities[spine].vendor,
                attrs={"speed_gbps": 100, "mtu": 9216,
                       "parent": spine, "peer_port": tor_port},
            ))
            t.add(Entity(
                tor_port, "switch_port", "underlay", t.entities[tor].vendor,
                attrs={"speed_gbps": 100, "mtu": 9216,
                       "parent": tor, "peer_port": sp_port},
            ))
            t.link(spine, sp_port, "has_port")
            t.link(tor, tor_port, "has_port")
            t.link(sp_port, tor_port, "connects_to", cable=f"cab-{spine}-{tor}")
            t.link(tor_port, sp_port, "connects_to", cable=f"cab-{spine}-{tor}")

    # ── ESX hosts (8, dual-homed) ────────────────────────────────────────
    host_assignments = [
        ("host-01", "tor-01", "tor-03", "rack-01", "cluster-prod"),
        ("host-02", "tor-01", "tor-03", "rack-01", "cluster-prod"),
        ("host-03", "tor-02", "tor-04", "rack-01", "cluster-prod"),
        ("host-04", "tor-02", "tor-04", "rack-01", "cluster-prod"),
        ("host-05", "tor-01", "tor-03", "rack-02", "cluster-edge"),
        ("host-06", "tor-02", "tor-04", "rack-02", "cluster-edge"),
        ("host-07", "tor-01", "tor-03", "rack-02", "cluster-mgmt"),
        ("host-08", "tor-02", "tor-04", "rack-02", "cluster-mgmt"),
    ]
    for hid, tor_a, tor_b, rack, cluster in host_assignments:
        t.add(Entity(
            hid, "esx_host", "physical", "vmware",
            attrs={"cluster": cluster, "rack": rack},
        ))
        # pNICs and host-side ToR ports
        for vmnic, tor in (("vmnic0", tor_a), ("vmnic1", tor_b)):
            pnic = f"pnic-{hid}-{vmnic}"
            t.add(Entity(
                pnic, "pnic", "physical", "vmware",
                attrs={"speed_gbps": 25, "mtu": 9000, "parent": hid},
            ))
            t.link(hid, pnic, "has_pnic")
            tor_host_port = f"port-{tor}-{hid}-{vmnic}"
            t.add(Entity(
                tor_host_port, "switch_port", "underlay", t.entities[tor].vendor,
                attrs={"speed_gbps": 25, "mtu": 9216,
                       "parent": tor, "facing": "host"},
            ))
            t.link(tor, tor_host_port, "has_port")
            t.link(pnic, tor_host_port, "connects_to")
            t.link(tor_host_port, pnic, "connects_to")
        # TEP per host
        tep = f"tep-{hid}"
        t.add(Entity(
            tep, "tep", "overlay", "vmware",
            attrs={"ip": f"10.20.0.{int(hid[-2:]) + 10}", "vlan": 1647,
                   "parent_host": hid},
        ))
        t.link(hid, tep, "has_tep")

    # ── TEP pairs (full mesh between cluster-prod hosts) ─────────────────
    prod_hosts = [h[0] for h in host_assignments if h[4] == "cluster-prod"]
    for i, ha in enumerate(prod_hosts):
        for hb in prod_hosts[i + 1:]:
            tp = f"teppair-{ha}-{hb}"
            t.add(Entity(tp, "tep_pair", "overlay", "vmware"))
            t.link(f"tep-{ha}", tp, "in_pair")
            t.link(f"tep-{hb}", tp, "in_pair")

    # ── NSX Edge nodes ───────────────────────────────────────────────────
    for i, host in enumerate(("host-05", "host-06"), start=1):
        edge = f"edge-{i:02d}"
        t.add(Entity(edge, "nsx_edge", "overlay", "vmware",
                     attrs={"asn": 65100, "parent_host": host}))
        t.link(host, edge, "hosts_vm")

    # ── T0, BGP sessions, TGW, Project, VPCs ─────────────────────────────
    t.add(Entity("t0-prod", "tier0", "overlay", "vmware",
                 attrs={"asn": 65100, "ha_mode": "active-standby"}))
    t.link("edge-01", "t0-prod", "hosts_sr")
    t.link("edge-02", "t0-prod", "hosts_sr")

    for tor in ("tor-01", "tor-02"):
        sess = f"bgp-t0-{tor}"
        t.add(Entity(
            sess, "bgp_session", "underlay", "multivendor",
            attrs={"local_asn": 65100,
                   "remote_asn": t.entities[tor].attrs["asn"],
                   "local_endpoint": "t0-prod",
                   "remote_endpoint": tor,
                   "remote_ip": f"10.10.0.{int(tor[-2:])}"},
        ))
        t.link("t0-prod", sess, "has_bgp")
        t.link(tor, sess, "has_bgp")

    t.add(Entity("proj-app", "nsx_project", "overlay", "vmware",
                 attrs={"display_name": "Application Project"}))
    t.add(Entity("tgw-app", "transit_gateway", "overlay", "vmware",
                 attrs={"type": "centralized"}))
    t.link("proj-app", "tgw-app", "has_tgw")
    t.link("tgw-app", "t0-prod", "uses_t0")

    # ── VPCs and segments ────────────────────────────────────────────────
    vpc_specs = [
        ("vpc-web", "10.50.1.0/24", ["seg-web", "seg-web-priv"]),
        ("vpc-api", "10.50.2.0/24", ["seg-api"]),
        ("vpc-db", "10.50.3.0/24", ["seg-db"]),
    ]
    for vpc_id, cidr, segs in vpc_specs:
        t.add(Entity(vpc_id, "vpc", "overlay", "vmware",
                     attrs={"cidr": cidr, "project": "proj-app"}))
        t.link("proj-app", vpc_id, "has_vpc")
        t.link(vpc_id, "tgw-app", "uses_tgw")
        for sid in segs:
            t.add(Entity(sid, "segment", "overlay", "vmware",
                         attrs={"vpc": vpc_id, "transport_zone": "tz-overlay"}))
            t.link(vpc_id, sid, "has_segment")
            for tp in [n for n in t.entities if n.startswith("teppair-")]:
                t.link(sid, tp, "encapsulated_by")

    # ── VMs ──────────────────────────────────────────────────────────────
    vm_layout = [
        ("vm-web-01", "seg-web", "host-01", "app-web"),
        ("vm-web-02", "seg-web", "host-02", "app-web"),
        ("vm-web-03", "seg-web", "host-03", "app-web"),
        ("vm-api-01", "seg-api", "host-01", "app-api"),
        ("vm-api-02", "seg-api", "host-04", "app-api"),
        ("vm-db-01", "seg-db", "host-02", "app-db"),
        ("vm-db-02", "seg-db", "host-04", "app-db"),
    ]
    for vid, seg, host, app in vm_layout:
        t.add(Entity(vid, "vm", "application", "vmware", attrs={"app": app}))
        t.link(vid, host, "runs_on")
        t.link(vid, seg, "attached_to")

    # ── Applications + dependency chain ──────────────────────────────────
    for app in ("app-web", "app-api", "app-db"):
        t.add(Entity(app, "application", "application", "n/a"))
    for vid, _, _, app in vm_layout:
        t.link(app, vid, "consists_of")
    t.link("app-web", "app-api", "depends_on", port=8080)
    t.link("app-api", "app-db", "depends_on", port=5432)

    # ── Distributed Firewall rules (NSX DFW) ─────────────────────────────
    # Default rule set allows the dependency chain. Scenarios mutate these.
    dfw_rules = [
        ("dfw-rule-001", "allow", "seg-web", "seg-api", 8080,
         "web → api allow", 100),
        ("dfw-rule-002", "allow", "seg-api", "seg-db", 5432,
         "api → db allow", 110),
        ("dfw-rule-003", "deny", "any", "seg-db", "any",
         "default deny to db", 999),
    ]
    for rid, action, src, dst, port, name, prio in dfw_rules:
        t.add(Entity(rid, "dfw_rule", "overlay", "vmware",
                     attrs={"action": action, "src": src, "dst": dst,
                            "port": port, "display_name": name,
                            "priority": prio}))
        t.link("proj-app", rid, "has_dfw_rule")

    return t
