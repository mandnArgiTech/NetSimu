// Layered preset layout for M1.
//
// We compute (x, y) per node ourselves rather than letting a force-directed
// layout decide. Reason: the lab's pedagogical promise is "you can SEE the
// layers". A force layout produces clouds; we want bands. cytoscape-dagre is
// pinned for M2+ when sub-views (in-context, packet-flow paths) need it.

import type { TopoNode } from "../api";

// Vertical band centres, top-to-bottom. CLAUDE.md: applications at top,
// physical at bottom (overlay floats between application and physical;
// underlay is the literal bottom).
const LAYER_Y: Record<string, number> = {
  application: 120,
  overlay: 420,
  physical: 820,
  underlay: 1100,
};

// Sub-row index within a band — lets multiple types stack inside one layer.
// Lower numbers are higher on screen.
const TYPE_SUBROW: Record<string, number> = {
  // application
  application: 0,
  vm: 1,

  // overlay (logical hierarchy: project at top, then VPC/segment, then
  // edge plumbing, then TEPs)
  nsx_project: 0,
  transit_gateway: 0,
  vpc: 1,
  segment: 2,
  dfw_rule: 2,
  tier0: 3,
  nsx_edge: 3,
  tep: 4,
  tep_pair: 5,

  // physical (hosts above their pNICs)
  esx_host: 0,
  pnic: 1,

  // underlay (spines + ToRs share the switch row, BGP under that, ports
  // last so they spread along the bottom)
  switch: 0,
  bgp_session: 1,
  switch_port: 2,
};

const SUB_ROW_GAP = 90;
const NODE_X_SPACING = 130;
const VIEWPORT_CENTER_X = 820;
const MAX_ROW_WIDTH = 1700;

export interface Position {
  x: number;
  y: number;
}

export function computePositions(nodes: TopoNode[]): Record<string, Position> {
  // Bucket by (layer, type) — each bucket lays out as one or more rows.
  const buckets = new Map<string, TopoNode[]>();
  for (const n of nodes) {
    const key = `${n.layer}::${n.type}`;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key)!.push(n);
  }

  const positions: Record<string, Position> = {};
  const perRow = Math.max(1, Math.floor(MAX_ROW_WIDTH / NODE_X_SPACING));

  for (const [key, group] of buckets.entries()) {
    const [layer, type] = key.split("::");
    const yBase = LAYER_Y[layer] ?? 500;
    const subRow = TYPE_SUBROW[type] ?? 0;

    // Deterministic order — alphabetical by id keeps spine-01 left of spine-02.
    group.sort((a, b) => a.id.localeCompare(b.id));

    group.forEach((n, i) => {
      const wrapRow = Math.floor(i / perRow);
      const col = i % perRow;
      const rowSize = Math.min(perRow, group.length - wrapRow * perRow);
      const totalWidth = (rowSize - 1) * NODE_X_SPACING;
      const xStart = VIEWPORT_CENTER_X - totalWidth / 2;
      positions[n.id] = {
        x: xStart + col * NODE_X_SPACING,
        y: yBase + (subRow + wrapRow) * SUB_ROW_GAP,
      };
    });
  }
  return positions;
}
