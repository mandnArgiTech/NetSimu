// Cytoscape stylesheet — light theme, ≥16px labels, color-coded by layer.
//
// Cytoscape's CSS-like syntax doesn't go through Tailwind, so the palette is
// duplicated here as constants. Keep these in sync with tailwind.config.js
// (the topology canvas is the place those colors actually show up).

import type cytoscape from "cytoscape";

// Per-layer fill / border. Muted enough that 100+ nodes don't overwhelm.
const LAYER_PALETTE = {
  physical: { bg: "#eef2f7", border: "#1e3a8a", text: "#0f172a" },
  underlay: { bg: "#e0ecf6", border: "#1d4ed8", text: "#0f172a" },
  overlay: { bg: "#dff5f0", border: "#0d9488", text: "#0f172a" },
  application: { bg: "#e6f4ea", border: "#15803d", text: "#0f172a" },
};

// Per-type shape — gives each class of entity a recognisable silhouette
// even before vendor SVG icons land in M2.
const TYPE_SHAPE: Record<string, cytoscape.Css.NodeShape> = {
  switch: "round-rectangle",
  switch_port: "ellipse",
  esx_host: "rectangle",
  pnic: "ellipse",
  tep: "diamond",
  tep_pair: "octagon",
  nsx_edge: "round-rectangle",
  tier0: "round-rectangle",
  bgp_session: "octagon",
  nsx_project: "round-rectangle",
  transit_gateway: "round-rectangle",
  vpc: "round-rectangle",
  segment: "round-rectangle",
  vm: "rectangle",
  application: "round-rectangle",
  dfw_rule: "ellipse",
};

// Smaller node sizes for high-cardinality types so 32 ports don't blow out
// the underlay band.
const TYPE_SIZE: Record<string, { w: number; h: number }> = {
  switch_port: { w: 70, h: 36 },
  pnic: { w: 70, h: 36 },
  tep_pair: { w: 90, h: 50 },
  bgp_session: { w: 100, h: 48 },
  dfw_rule: { w: 110, h: 48 },
  vm: { w: 110, h: 60 },
};

const DEFAULT_SIZE = { w: 130, h: 70 };

export function buildStylesheet(): cytoscape.Stylesheet[] {
  const sheet: cytoscape.Stylesheet[] = [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "text-valign": "center",
        "text-halign": "center",
        "text-wrap": "wrap",
        "text-max-width": "120px",
        "font-size": "16px", // CLAUDE.md hard rule: never below 16px.
        "font-family":
          "Inter, Segoe UI, system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
        "font-weight": 500,
        color: "#0f172a",
        "background-color": "#ffffff",
        "border-width": 2,
        "border-color": "#94a3b8",
        width: DEFAULT_SIZE.w,
        height: DEFAULT_SIZE.h,
        shape: "round-rectangle",
        "text-outline-width": 0,
      },
    },
    {
      selector: "edge",
      style: {
        width: 1.5,
        "line-color": "#cbd5e1",
        "target-arrow-color": "#cbd5e1",
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
        opacity: 0.55,
        // Edge labels stay off in M1 — they'd overwhelm at this scale. M2
        // will surface the rel name on hover/highlight.
        "font-size": "16px",
        color: "#475569",
      },
    },
    // Layer-colored fills/borders.
    ...Object.entries(LAYER_PALETTE).map(([layer, p]) => ({
      selector: `node[layer = "${layer}"]`,
      style: {
        "background-color": p.bg,
        "border-color": p.border,
        color: p.text,
      },
    })),
    // Per-type shapes.
    ...Object.entries(TYPE_SHAPE).map(([type, shape]) => ({
      selector: `node[type = "${type}"]`,
      style: { shape },
    })),
    // Per-type sizes (override default).
    ...Object.entries(TYPE_SIZE).map(([type, size]) => ({
      selector: `node[type = "${type}"]`,
      style: { width: size.w, height: size.h },
    })),
    // Edge color hint by relationship — keep it subtle.
    {
      selector: "edge[rel = \"connects_to\"]",
      style: { "line-color": "#94a3b8", opacity: 0.7 },
    },
    {
      selector: "edge[rel = \"has_bgp\"]",
      style: { "line-color": "#1d4ed8", opacity: 0.8, width: 2 },
    },
    {
      selector: "edge[rel = \"depends_on\"]",
      style: { "line-color": "#15803d", opacity: 0.8, width: 2 },
    },
  ];
  return sheet;
}
