import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import cytoscape from "cytoscape";
import type { Core, ElementDefinition, NodeSingular } from "cytoscape";
import expandCollapse from "cytoscape-expand-collapse";

import type { SavedPositions, TopoNode, TopologyResponse } from "../api";
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

const HIDDEN_EDGE_RELS = new Set<string>([
  "encapsulated_by",
  "in_pair",
  "uses_tgw",
  "uses_t0",
  "hosts_sr",
  "has_dfw_rule",
  "has_tgw",
  "has_vpc",
  "has_segment",
  "consists_of",
  "hosts_vm",
]);

const HIDDEN_NODE_TYPES = new Set<string>(["tep_pair", "bgp_session"]);

export interface HoverPayload {
  node: TopoNode;
  /** Page-coordinate position of the cursor, for tooltip placement. */
  pageX: number;
  pageY: number;
}

export interface CanvasHandle {
  getPositions(): SavedPositions;
  /** Highlight + center on a node (used by Connections list). */
  selectNode(id: string): void;
}

interface CanvasProps {
  topology: TopologyResponse;
  savedPositions: SavedPositions;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onHover: (payload: HoverPayload | null) => void;
}

export const Canvas = forwardRef<CanvasHandle, CanvasProps>(function Canvas(
  { topology, savedPositions, selectedId, onSelect, onHover },
  ref,
) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  // Lookup of leaf-node TopoNodes (the canvas may show compound parents
  // we don't have a topology entry for, but here every node is real).
  const nodeIndexRef = useRef<Map<string, TopoNode>>(new Map());

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
    let hoverTimer: ReturnType<typeof setTimeout> | null = null;
    cy.on("mouseover", "node", (evt) => {
      const n = evt.target as NodeSingular;
      const id = n.id();
      const node = nodeIndexRef.current.get(id);
      if (!node) return;
      // Cytoscape's renderedPosition is canvas-relative; we want page coords.
      const renderedPos = n.renderedPosition();
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const pageX = rect.left + renderedPos.x;
      const pageY = rect.top + renderedPos.y;
      if (hoverTimer) clearTimeout(hoverTimer);
      hoverTimer = setTimeout(() => {
        onHover({ node, pageX, pageY });
      }, 200);
    });
    cy.on("mouseout", "node", () => {
      if (hoverTimer) {
        clearTimeout(hoverTimer);
        hoverTimer = null;
      }
      onHover(null);
    });

    // ── Click: select for the detail panel; expand-collapse for parents ─
    cy.on("tap", "node", (evt) => {
      const n = evt.target as NodeSingular;
      // Compound parents handle their own expand/collapse first — clicking
      // a collapsed compound reveals children rather than opening a panel.
      if (api.isExpandable(n)) {
        api.expand(n);
        return;
      }
      if (n.isParent() && api.isCollapsible(n) && evt.target === n) {
        // Don't open the panel when clicking the bare chrome of an
        // expanded parent (that means "collapse me").
        api.collapse(n);
        return;
      }
      onSelect(n.id());
    });
    cy.on("tap", (evt) => {
      // Tap on background (no target node) → deselect.
      if (evt.target === cy) onSelect(null);
    });

    return () => {
      if (hoverTimer) clearTimeout(hoverTimer);
      cy.destroy();
      cyRef.current = null;
    };
  }, [topology, savedPositions, onSelect, onHover]);

  // Sync external selectedId → cytoscape's :selected state.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.$("node:selected").unselect();
    if (selectedId) {
      const target = cy.getElementById(selectedId);
      if (target.length > 0) target.select();
    }
  }, [selectedId]);

  return <div ref={containerRef} className="cy-canvas" />;
});
