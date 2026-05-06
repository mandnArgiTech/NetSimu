// Cytoscape stylesheet — light theme, ≥16px labels, color-coded by layer.
//
// Compound parents (host, switch, NSX project, VPC, application) get a
// distinct visual treatment: dashed border, label at top, semi-transparent
// fill so children show through. Collapsed compounds get a stronger fill
// and a child-count badge — they read as "click me to drill in".
//
// Cytoscape's CSS-like syntax doesn't go through Tailwind, so the palette
// is duplicated here as constants. Keep these in sync with
// tailwind.config.js (the canvas is the place those colors actually show).

import type cytoscape from "cytoscape";

const LAYER_PALETTE = {
  physical: { bg: "#eef2f7", border: "#1e3a8a", text: "#0f172a" },
  underlay: { bg: "#e0ecf6", border: "#1d4ed8", text: "#0f172a" },
  overlay: { bg: "#dff5f0", border: "#0d9488", text: "#0f172a" },
  application: { bg: "#e6f4ea", border: "#15803d", text: "#0f172a" },
};

const TYPE_SHAPE: Record<string, cytoscape.Css.NodeShape> = {
  switch: "round-rectangle",
  switch_port: "ellipse",
  esx_host: "round-rectangle",
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
  vm: "round-rectangle",
  application: "round-rectangle",
  dfw_rule: "ellipse",
};

// Sizes for leaf nodes. Compound parents auto-size to their children.
const TYPE_SIZE: Record<string, { w: number; h: number }> = {
  switch_port: { w: 70, h: 36 },
  pnic: { w: 80, h: 40 },
  tep: { w: 90, h: 50 },
  tep_pair: { w: 100, h: 52 },
  bgp_session: { w: 110, h: 50 },
  dfw_rule: { w: 130, h: 52 },
  vm: { w: 130, h: 60 },
  segment: { w: 130, h: 56 },
  transit_gateway: { w: 140, h: 56 },
  tier0: { w: 140, h: 60 },
  nsx_edge: { w: 130, h: 56 },
};

const DEFAULT_SIZE = { w: 130, h: 64 };

export function buildStylesheet(): cytoscape.Stylesheet[] {
  const sheet: cytoscape.Stylesheet[] = [
    // ── Default node ──────────────────────────────────────────────────
    {
      selector: "node",
      style: {
        label: "data(label)",
        "text-valign": "center",
        "text-halign": "center",
        "text-wrap": "wrap",
        "text-max-width": "120px",
        "font-size": "16px", // CLAUDE.md: never below 16px.
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
      },
    },
    // ── Default edge ──────────────────────────────────────────────────
    {
      selector: "edge",
      style: {
        width: 1.5,
        "line-color": "#cbd5e1",
        "target-arrow-color": "#cbd5e1",
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
        opacity: 0.6,
        "font-size": "16px",
        color: "#475569",
      },
    },
    // ── Layer-coloured fills/borders (leaves) ─────────────────────────
    ...Object.entries(LAYER_PALETTE).map(([layer, p]) => ({
      selector: `node[layer = "${layer}"]`,
      style: {
        "background-color": p.bg,
        "border-color": p.border,
        color: p.text,
      },
    })),
    // ── Per-type shape ────────────────────────────────────────────────
    ...Object.entries(TYPE_SHAPE).map(([type, shape]) => ({
      selector: `node[type = "${type}"]`,
      style: { shape },
    })),
    // ── Per-type size (leaf) ──────────────────────────────────────────
    ...Object.entries(TYPE_SIZE).map(([type, size]) => ({
      selector: `node[type = "${type}"]`,
      style: { width: size.w, height: size.h },
    })),
    // ── Compound parents (expanded) ───────────────────────────────────
    // Dashed border, label at top, semi-transparent fill so children show.
    // `padding` and `text-margin-y` are valid Cytoscape CSS but missing
    // from @types/cytoscape — cast keeps TS quiet without losing them.
    {
      selector: ":parent",
      style: {
        "background-opacity": 0.2,
        "border-width": 2,
        "border-style": "dashed",
        "text-valign": "top",
        "text-halign": "center",
        "font-size": "18px",
        "font-weight": 600,
        padding: "16px",
        "text-margin-y": -6,
      },
    } as unknown as cytoscape.Stylesheet,
    // ── Collapsed compounds — strong fill + + cue ──────────────────────
    // The expand-collapse plugin adds the .cy-expand-collapse-collapsed-node
    // class on collapsed parents.
    {
      selector: "node.cy-expand-collapse-collapsed-node",
      style: {
        "background-opacity": 0.85,
        "border-style": "solid",
        "border-width": 3,
        "text-valign": "center",
        shape: "round-rectangle",
        width: 160,
        height: 70,
        "font-size": "16px",
        "font-weight": 600,
      },
    },
    // ── Edge styles by relation ───────────────────────────────────────
    {
      selector: 'edge[rel = "connects_to"]',
      style: { "line-color": "#94a3b8", opacity: 0.7 },
    },
    {
      selector: 'edge[rel = "has_bgp"]',
      style: { "line-color": "#1d4ed8", opacity: 0.85, width: 2 },
    },
    {
      selector: 'edge[rel = "depends_on"]',
      style: { "line-color": "#15803d", opacity: 0.9, width: 2.5 },
    },
    {
      selector: 'edge[rel = "runs_on"]',
      style: { "line-color": "#475569", opacity: 0.6, "line-style": "dashed" },
    },
    {
      selector: 'edge[rel = "attached_to"]',
      style: { "line-color": "#0d9488", opacity: 0.75 },
    },
  ];
  return sheet;
}
