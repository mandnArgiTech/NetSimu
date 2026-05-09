import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import cytoscape from "cytoscape";
import type {
  Core,
  EdgeSingular,
  ElementDefinition,
  NodeSingular,
} from "cytoscape";
import expandCollapse from "cytoscape-expand-collapse";

import type {
  SavedPositions,
  TopoEdge,
  TopoNode,
  TopologyResponse,
} from "../api";
import { buildStylesheet } from "./style";
import { buildParentMap, COLLAPSED_BY_DEFAULT_TYPES } from "./parents";
import { computePositions } from "./layout";

cytoscape.use(expandCollapse);

interface ExpandCollapseApi {
  collapse: (nodes: cytoscape.NodeCollection) => void;
  expand: (nodes: cytoscape.NodeCollection | cytoscape.NodeSingular) => void;
  isCollapsible: (n: cytoscape.NodeSingular) => boolean;
  isExpandable: (n: cytoscape.NodeSingular) => boolean;
}

const COMPOUND_RELS = new Set<string>(["has_port", "has_pnic", "has_tep"]);

// Edges hidden from the canvas. Kept tight on purpose: every other rel
// teaches something. `encapsulated_by` would draw 24 mesh lines from each
// segment to every TEP pair (visual chaos). `in_pair` is internal to the
// TEP-pair node and already implied by it.
//
// Containment rels (has_vpc, has_segment, consists_of, etc.) and reference
// rels (uses_t0, uses_tgw) are kept visible — see style.ts for the dotted
// vs solid styling that distinguishes them from data-plane edges.
const HIDDEN_EDGE_RELS = new Set<string>([
  "encapsulated_by",
  "in_pair",
]);

const HIDDEN_NODE_TYPES = new Set<string>(["tep_pair", "bgp_session"]);

export type HoverPayload =
  | {
      kind: "node";
      node: TopoNode;
      /** Page-coordinate position of the cursor, for tooltip placement. */
      pageX: number;
      pageY: number;
    }
  | {
      kind: "edge";
      edge: TopoEdge;
      pageX: number;
      pageY: number;
    };

export type Selection =
  | { kind: "node"; id: string }
  | { kind: "edge"; id: string };

export interface CanvasHandle {
  getPositions(): SavedPositions;
  /** Highlight + center on a node (used by Connections list). */
  selectNode(id: string): void;
}

interface CanvasProps {
  topology: TopologyResponse;
  savedPositions: SavedPositions;
  selection: Selection | null;
  onSelect: (sel: Selection | null) => void;
  onHover: (payload: HoverPayload | null) => void;
}

export const Canvas = forwardRef<CanvasHandle, CanvasProps>(function Canvas(
  { topology, savedPositions, selection, onSelect, onHover },
  ref,
) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  // Lookup of leaf-node TopoNodes (the canvas may show compound parents
  // we don't have a topology entry for, but here every node is real).
  const nodeIndexRef = useRef<Map<string, TopoNode>>(new Map());
  const edgeIndexRef = useRef<Map<string, TopoEdge>>(new Map());

  useImperativeHandle(
    ref,
    () => ({
      getPositions(): SavedPositions {
        const cy = cyRef.current;
        if (!cy) return {};
        const out: SavedPositions = {};
        cy.nodes().forEach((n) => {
          const p = n.position();
          out[n.id()] = { x: p.x, y: p.y };
        });
        return out;
      },
      selectNode(id: string) {
        const cy = cyRef.current;
        if (!cy) return;
        const target = cy.getElementById(id);
        if (target.length === 0) return;
        cy.$("node:selected").unselect();
        target.select();
        cy.animate({ center: { eles: target }, zoom: cy.zoom() }, { duration: 250 });
      },
    }),
    [],
  );

  useEffect(() => {
    if (!containerRef.current) return;

    const visibleNodes = topology.nodes.filter(
      (n) => !HIDDEN_NODE_TYPES.has(n.type),
    );
    const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));
    nodeIndexRef.current = new Map(visibleNodes.map((n) => [n.id, n]));

    const visibleEdges = topology.edges.filter(
      (e) =>
        !HIDDEN_EDGE_RELS.has(e.rel) &&
        !COMPOUND_RELS.has(e.rel) &&
        visibleNodeIds.has(e.source) &&
        visibleNodeIds.has(e.target),
    );
    edgeIndexRef.current = new Map(visibleEdges.map((e) => [e.id, e]));

    const parentMap = buildParentMap(topology.edges);
    const computed = computePositions(visibleNodes, topology.edges);

    const positions: SavedPositions = { ...computed };
    for (const [id, p] of Object.entries(savedPositions)) {
      if (visibleNodeIds.has(id)) positions[id] = p;
    }

    const elements: ElementDefinition[] = [
      ...visibleNodes.map((n) => ({
        data: {
          id: n.id,
          label: n.label,
          type: n.type,
          layer: n.layer,
          vendor: n.vendor,
          type_label: n.type_label,
          parent: parentMap.get(n.id),
        },
        position: positions[n.id],
      })),
      ...visibleEdges.map((e) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          rel: e.rel,
        },
      })),
    ];

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: buildStylesheet(),
      layout: { name: "preset" },
      wheelSensitivity: 0.2,
      minZoom: 0.1,
      maxZoom: 3,
    });
    cyRef.current = cy;

    const api = (
      cy as unknown as { expandCollapse: (o: object) => ExpandCollapseApi }
    ).expandCollapse({
      layoutBy: { name: "preset" },
      fisheye: false,
      animate: false,
      undoable: false,
      cueEnabled: true,
      expandCollapseCueSize: 16,
      expandCollapseCuePosition: "top-left",
    });

    const initiallyCollapsed = cy
      .nodes()
      .filter((n) => COLLAPSED_BY_DEFAULT_TYPES.has(n.data("type")));
    if (initiallyCollapsed.length) api.collapse(initiallyCollapsed);
    cy.fit(undefined, 60);

    // ── Hover (200ms delay per design doc § 3a) ─────────────────────────
    // We use a cursor-tracking approach: on each mousemove the renderer
    // gives us page coords, which we use as the tooltip anchor. Node
    // hover uses node.renderedPosition() for stable placement; edge
    // hover follows the cursor because edges have no single "centroid"
    // the user would naturally read from.
    let hoverTimer: ReturnType<typeof setTimeout> | null = null;
    const cancelHover = () => {
      if (hoverTimer) {
        clearTimeout(hoverTimer);
        hoverTimer = null;
      }
      onHover(null);
    };

    cy.on("mouseover", "node", (evt) => {
      const n = evt.target as NodeSingular;
      const node = nodeIndexRef.current.get(n.id());
      if (!node) return;
      const renderedPos = n.renderedPosition();
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const pageX = rect.left + renderedPos.x;
      const pageY = rect.top + renderedPos.y;
      if (hoverTimer) clearTimeout(hoverTimer);
      hoverTimer = setTimeout(() => {
        onHover({ kind: "node", node, pageX, pageY });
      }, 200);
    });
    cy.on("mouseout", "node", cancelHover);

    cy.on("mouseover", "edge", (evt) => {
      const e = evt.target as EdgeSingular;
      const edge = edgeIndexRef.current.get(e.id());
      if (!edge) return;
      const orig = (evt.originalEvent as MouseEvent | undefined) ?? null;
      // For edges we follow the cursor — there's no obvious centroid.
      const pageX = orig?.pageX ?? e.midpoint().x;
      const pageY = orig?.pageY ?? e.midpoint().y;
      if (hoverTimer) clearTimeout(hoverTimer);
      hoverTimer = setTimeout(() => {
        onHover({ kind: "edge", edge, pageX, pageY });
      }, 200);
    });
    cy.on("mouseout", "edge", cancelHover);

    // ── Click: open the detail panel AND, for compound parents, toggle
    // expand/collapse. The user expects "I clicked the spine, show me the
    // spine" — so the panel always opens, regardless of expand state.
    cy.on("tap", "node", (evt) => {
      const n = evt.target as NodeSingular;
      if (api.isExpandable(n)) {
        api.expand(n);
      } else if (n.isParent() && api.isCollapsible(n) && evt.target === n) {
        api.collapse(n);
      }
      onSelect({ kind: "node", id: n.id() });
    });
    cy.on("tap", "edge", (evt) => {
      const e = evt.target as EdgeSingular;
      onSelect({ kind: "edge", id: e.id() });
    });
    cy.on("tap", (evt) => {
      // Tap on background (no target) → deselect.
      if (evt.target === cy) onSelect(null);
    });

    return () => {
      if (hoverTimer) clearTimeout(hoverTimer);
      cy.destroy();
      cyRef.current = null;
    };
  }, [topology, savedPositions, onSelect, onHover]);

  // Sync external selection → cytoscape's :selected state for the right
  // element class (nodes and edges have separate :selected styling).
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.$(":selected").unselect();
    if (selection) {
      const target = cy.getElementById(selection.id);
      if (target.length > 0) target.select();
    }
  }, [selection]);

  return <div ref={containerRef} className="cy-canvas" />;
});
