// Strict hierarchical preset layout for M1.
//
// Mirrors the tree the user drew:
//   spines (top)
//   ToRs
//   ESX hosts (compound — wraps pNICs, TEPs)
//   NSX overlay (T0, TGW, NSX project, NSX edges)
//   VPCs
//   Segments + DFW rules
//   VMs (anchored to runs_on host)
//   Applications (anchored to consumed VMs) (bottom)
//
// Hidden in M1 (re-introduced in M2 with proper context):
//   bgp_session, tep_pair — they sit between two parents, no clean rank.
//
// Compound parents:
//   host  → pnics, teps (visible only when host expanded)
//   switch → switch_ports (visible only when switch expanded)

import type { TopoEdge, TopoNode } from "../api";

export interface Position {
  x: number;
  y: number;
}

// Canvas main column.
const W = { left: 140, right: 1880 };

// Vertical ranks (top → bottom).
const Y = {
  spine: 100,
  tor: 320,
  host: 580,
  nsxRow1: 800, // T0, TGW, NSX project, NSX edges
  vpc: 940,
  segDfwRow: 1080, // segments + DFW rules
  vm: 1220,
  app: 1360,
};

// ── Helpers ─────────────────────────────────────────────────────────────
function spread(count: number, leftEdge: number, rightEdge: number): number[] {
  if (count <= 0) return [];
  if (count === 1) return [(leftEdge + rightEdge) / 2];
  const step = (rightEdge - leftEdge) / (count - 1);
  return Array.from({ length: count }, (_, i) => leftEdge + i * step);
}

function avg(xs: number[]): number {
  return xs.reduce((s, v) => s + v, 0) / xs.length;
}

// ── Main entry ──────────────────────────────────────────────────────────
export function computePositions(
  nodes: TopoNode[],
  edges: TopoEdge[],
): Record<string, Position> {
  // Parent maps from edges.
  const hostOfPnic = new Map<string, string>();
  const hostOfTep = new Map<string, string>();
  const hostOfVm = new Map<string, string>();
  const switchOfPort = new Map<string, string>();
  const vmsOfApp = new Map<string, string[]>();

  for (const e of edges) {
    if (e.rel === "has_pnic") hostOfPnic.set(e.target, e.source);
    else if (e.rel === "has_tep") hostOfTep.set(e.target, e.source);
    else if (e.rel === "runs_on") hostOfVm.set(e.source, e.target);
    else if (e.rel === "has_port") switchOfPort.set(e.target, e.source);
    else if (e.rel === "consists_of") {
      const arr = vmsOfApp.get(e.source) ?? [];
      arr.push(e.target);
      vmsOfApp.set(e.source, arr);
    }
  }

  const pos: Record<string, Position> = {};

  // ── Spines (top) ──
  const spines = nodes
    .filter((n) => n.type === "switch" && n.attrs?.role === "spine")
    .sort((a, b) => a.id.localeCompare(b.id));
  const spineXs = spread(spines.length, W.left + 350, W.right - 350);
  spines.forEach((n, i) => {
    pos[n.id] = { x: spineXs[i], y: Y.spine };
  });

  // ── ToRs ──
  const tors = nodes
    .filter((n) => n.type === "switch" && n.attrs?.role === "tor")
    .sort((a, b) => a.id.localeCompare(b.id));
  const torXs = spread(tors.length, W.left + 150, W.right - 150);
  tors.forEach((n, i) => {
    pos[n.id] = { x: torXs[i], y: Y.tor };
  });

  // ── Hosts (8 in a row) ──
  const hosts = nodes
    .filter((n) => n.type === "esx_host")
    .sort((a, b) => a.id.localeCompare(b.id));
  const hostXs = spread(hosts.length, W.left + 50, W.right - 50);
  hosts.forEach((n, i) => {
    pos[n.id] = { x: hostXs[i], y: Y.host };
  });

  // ── pNICs and TEPs inside their host (small offset within parent) ──
  for (const n of nodes) {
    if (n.type === "pnic") {
      const h = hostOfPnic.get(n.id);
      if (h && pos[h]) {
        const left = n.id.endsWith("vmnic0");
        pos[n.id] = { x: pos[h].x + (left ? -45 : 45), y: pos[h].y + 22 };
      }
    } else if (n.type === "tep") {
      const h = hostOfTep.get(n.id);
      if (h && pos[h]) {
        pos[n.id] = { x: pos[h].x, y: pos[h].y - 24 };
      }
    }
  }

  // ── Switch ports clustered tight to parent ──
  // Spines have 4 ports, ToRs have 6. Place them in 1-2 rows directly under
  // the parent so the compound box stays compact when expanded.
  const portsByParent = new Map<string, TopoNode[]>();
  for (const n of nodes) {
    if (n.type !== "switch_port") continue;
    const sw = switchOfPort.get(n.id);
    if (!sw) continue;
    const arr = portsByParent.get(sw) ?? [];
    arr.push(n);
    portsByParent.set(sw, arr);
  }
  for (const [sw, ports] of portsByParent) {
    const swPos = pos[sw];
    if (!swPos) continue;
    ports.sort((a, b) => a.id.localeCompare(b.id));
    const perRow = 3;
    const rowGap = 32;
    const colGap = 60;
    ports.forEach((p, i) => {
      const row = Math.floor(i / perRow);
      const col = i % perRow;
      const rowSize = Math.min(perRow, ports.length - row * perRow);
      const xOffsets = spread(rowSize, -((rowSize - 1) * colGap) / 2, ((rowSize - 1) * colGap) / 2);
      pos[p.id] = {
        x: swPos.x + xOffsets[col],
        y: swPos.y + 30 + row * rowGap,
      };
    });
  }

  // ── NSX overlay row 1: T0, TGW, NSX project, NSX edges ──
  const nsxRow1Items: TopoNode[] = [];
  const t0 = nodes.find((n) => n.type === "tier0");
  const tgw = nodes.find((n) => n.type === "transit_gateway");
  const proj = nodes.find((n) => n.type === "nsx_project");
  if (t0) nsxRow1Items.push(t0);
  if (tgw) nsxRow1Items.push(tgw);
  if (proj) nsxRow1Items.push(proj);
  const nsxEdges = nodes
    .filter((n) => n.type === "nsx_edge")
    .sort((a, b) => a.id.localeCompare(b.id));
  nsxRow1Items.push(...nsxEdges);
  const nsxRow1Xs = spread(nsxRow1Items.length, W.left + 100, W.right - 100);
  nsxRow1Items.forEach((n, i) => {
    pos[n.id] = { x: nsxRow1Xs[i], y: Y.nsxRow1 };
  });

  // ── VPCs ──
  const vpcs = nodes
    .filter((n) => n.type === "vpc")
    .sort((a, b) => a.id.localeCompare(b.id));
  const vpcXs = spread(vpcs.length, W.left + 250, W.right - 250);
  vpcs.forEach((n, i) => {
    pos[n.id] = { x: vpcXs[i], y: Y.vpc };
  });

  // ── Segments + DFW rules row ──
  const segDfw = [
    ...nodes.filter((n) => n.type === "segment").sort((a, b) => a.id.localeCompare(b.id)),
    ...nodes.filter((n) => n.type === "dfw_rule").sort((a, b) => a.id.localeCompare(b.id)),
  ];
  const segDfwXs = spread(segDfw.length, W.left + 50, W.right - 50);
  segDfw.forEach((n, i) => {
    pos[n.id] = { x: segDfwXs[i], y: Y.segDfwRow };
  });

  // ── VMs anchored to host x; multiple VMs per host fan out ──
  const vmsByHost = new Map<string, TopoNode[]>();
  for (const n of nodes) {
    if (n.type !== "vm") continue;
    const h = hostOfVm.get(n.id);
    if (!h) continue;
    const arr = vmsByHost.get(h) ?? [];
    arr.push(n);
    vmsByHost.set(h, arr);
  }
  for (const [h, vms] of vmsByHost) {
    const hPos = pos[h];
    if (!hPos) continue;
    vms.sort((a, b) => a.id.localeCompare(b.id));
    if (vms.length === 1) {
      pos[vms[0].id] = { x: hPos.x, y: Y.vm };
    } else {
      const xs = spread(vms.length, hPos.x - 75, hPos.x + 75);
      vms.forEach((v, i) => {
        pos[v.id] = { x: xs[i], y: Y.vm };
      });
    }
  }

  // ── Applications anchored to avg consumed VM x ──
  const apps = nodes
    .filter((n) => n.type === "application")
    .sort((a, b) => a.id.localeCompare(b.id));
  for (const a of apps) {
    const vmIds = vmsOfApp.get(a.id) ?? [];
    const xs = vmIds.map((id) => pos[id]?.x).filter((x): x is number => x !== undefined);
    pos[a.id] = {
      x: xs.length ? avg(xs) : (W.left + W.right) / 2,
      y: Y.app,
    };
  }

  // ── Fallback for any unplaced node (off-screen) ──
  for (const n of nodes) {
    if (!pos[n.id]) pos[n.id] = { x: -2000, y: -2000 };
  }

  return pos;
}
