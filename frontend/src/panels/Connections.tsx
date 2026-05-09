// Connections tab — list every edge in/out of the selected node, grouped
// by direction. Each row is clickable to refocus the panel/canvas on the
// connected entity.

import type { TopoEdge, TopoNode } from "../api";

interface ConnectionsProps {
  selected: TopoNode;
  nodes: TopoNode[];
  edges: TopoEdge[];
  onSelect: (id: string) => void;
}

interface Row {
  id: string;
  rel: string;
  direction: "out" | "in";
}

// Friendly labels for the relationship names that show up here.
const REL_LABEL: Record<string, string> = {
  has_port: "owns port",
  has_pnic: "owns pNIC",
  has_tep: "owns TEP",
  hosts_vm: "hosts VM",
  hosts_sr: "hosts service router",
  has_bgp: "BGP peer",
  has_segment: "owns segment",
  has_vpc: "owns VPC",
  has_tgw: "owns TGW",
  has_dfw_rule: "owns DFW rule",
  consists_of: "includes VM",
  runs_on: "runs on",
  attached_to: "attached to",
  in_pair: "member of pair",
  encapsulated_by: "encapsulated via",
  uses_t0: "uses T0",
  uses_tgw: "uses TGW",
  connects_to: "wired to",
  depends_on: "depends on",
};

export function Connections({ selected, nodes, edges, onSelect }: ConnectionsProps) {
  const byId = new Map(nodes.map((n) => [n.id, n] as const));
  const rows: Row[] = [];
  for (const e of edges) {
    if (e.source === selected.id) {
      rows.push({ id: e.target, rel: e.rel, direction: "out" });
    } else if (e.target === selected.id) {
      rows.push({ id: e.source, rel: e.rel, direction: "in" });
    }
  }

  if (rows.length === 0) {
    return (
      <p className="text-base" style={{ color: "var(--text-secondary)" }}>
        No connections recorded.
      </p>
    );
  }

  return (
    <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
      {rows.map((r, i) => {
        const peer = byId.get(r.id);
        const label = REL_LABEL[r.rel] ?? r.rel;
        return (
          <li
            key={`${r.id}-${r.rel}-${i}`}
            style={{
              padding: "10px 0",
              borderBottom: "1px solid var(--border-soft)",
            }}
          >
            <div className="text-base" style={{ color: "var(--text-secondary)" }}>
              {r.direction === "out" ? "→ " : "← "}
              {label}
            </div>
            <button
              type="button"
              onClick={() => onSelect(r.id)}
              style={{
                background: "none",
                border: "none",
                padding: 0,
                color: "#1d4ed8",
                cursor: peer ? "pointer" : "default",
                fontSize: 17,
                fontWeight: 500,
                textAlign: "left",
                textDecoration: peer ? "underline" : "none",
              }}
              disabled={!peer}
            >
              {peer ? `${peer.id} (${peer.type_label})` : `${r.id} (unknown)`}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
