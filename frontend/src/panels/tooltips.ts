// One-line hover tooltips. Tone: senior engineer over coffee — informal,
// concrete, no fluff. Per design doc § 3a.
//
// Keyed primarily by entity type. A few types differentiate by attrs
// (spine vs ToR — both "switch" in the topology — and Cisco vs Arista
// flavor on ToR labels).

import type { TopoNode } from "../api";

const TYPE_TOOLTIPS: Record<string, string> = {
  switch_port:
    "Switch port — single physical interface with its own MTU, VLANs, and counters.",
  esx_host:
    "ESX host — physical server running ESXi. Owns pNICs, runs a TEP, hosts VMs.",
  pnic: "Physical NIC — host's wire to the underlay. Carries trunked VLANs.",
  tep: "Tunnel Endpoint — wraps VM packets into Geneve so the underlay can carry them.",
  tep_pair:
    "TEP pair — telemetry edge between two host TEPs. Health = both ends + the underlay path between them.",
  nsx_edge:
    "NSX Edge — VM that runs T0 services: north-south routing, NAT, load balancing.",
  tier0:
    "Tier-0 gateway — NSX router that bridges overlay and the outside world via BGP.",
  bgp_session:
    "BGP session — TCP peering exchanging route prefixes. State should be Established.",
  nsx_project:
    "NSX Project — multi-tenant boundary. Owns its own VPCs, segments, DFW rules.",
  transit_gateway:
    "Transit Gateway — hub router inside a Project. VPCs attach to it; it attaches to T0.",
  vpc: "VPC — self-contained virtual network with its own CIDR and segments.",
  segment:
    "Segment — NSX overlay network. VMs attached here think they're on the same Layer 2.",
  vm: "Virtual machine — guest OS running on an ESX host, attached to a segment.",
  application:
    "Application — logical grouping of VMs that together provide a service.",
  dfw_rule:
    "DFW rule — one line of distributed-firewall policy. Source, destination, port, allow/deny.",
};

const SWITCH_SPINE_TIP =
  "Spine switch — top of the leaf-spine fabric. Forwards traffic between ToRs at line rate.";
const SWITCH_TOR_TIP =
  "Top-of-Rack switch — every server in the rack lands here. Peers BGP with the NSX T0.";

export function tooltipFor(node: TopoNode): string {
  if (node.type === "switch") {
    const role = (node.attrs as { role?: string } | undefined)?.role;
    return role === "spine" ? SWITCH_SPINE_TIP : SWITCH_TOR_TIP;
  }
  return TYPE_TOOLTIPS[node.type] ?? `${node.type_label} — ${node.id}`;
}

// Resolves the concept id for the deep-dive panel given a node.
// Spines and ToRs share node.type "switch" — we route them to different
// concept files because the explanation is different.
export function conceptIdFor(node: TopoNode): string {
  if (node.type === "switch") {
    const role = (node.attrs as { role?: string } | undefined)?.role;
    return role === "spine" ? "spine" : "tor";
  }
  return node.type;
}
