import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import type { Core, ElementDefinition } from "cytoscape";
import expandCollapse from "cytoscape-expand-collapse";

import type { TopologyResponse } from "../api";
import { buildStylesheet } from "./style";
import { buildParentMap, COLLAPSED_BY_DEFAULT_TYPES } from "./parents";
import { computePositions } from "./layout";

cytoscape.use(expandCollapse);

// Minimal subset of the expand-collapse plugin's API surface that we use.
interface ExpandCollapseApi {
  collapse: (nodes: cytoscape.NodeCollection) => void;
  expand: (nodes: cytoscape.NodeCollection | cytoscape.NodeSingular) => void;
  isCollapsible: (n: cytoscape.NodeSingular) => boolean;
  isExpandable: (n: cytoscape.NodeSingular) => boolean;
}

// Edges that just express "X is part of compound Y" — already encoded via
// Cytoscape's parent field, so don't draw them as edges too.
const COMPOUND_RELS = new Set<string>([
  "has_port",
  "has_pnic",
  "has_tep",
]);

// Visually noisy edges hidden in M1; M2 will surface them on hover or in
// the in-context detail panel.
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

// Node types skipped entirely in M1 — they sit between two parents and
// don't read as a chip on their own. Reappear in M2 with proper context.
const HIDDEN_NODE_TYPES = new Set<string>([
  "tep_pair",
  "bgp_session",
]);

interface CanvasProps {
  topology: TopologyResponse;
}

export function Canvas({ topology }: CanvasProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);

  useEffect(() => {
    if (!ref.current) return;

    const visibleNodes = topology.nodes.filter(
      (n) => !HIDDEN_NODE_TYPES.has(n.type),
    );
    const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));

    const visibleEdges = topology.edges.filter(
      (e) =>
        !HIDDEN_EDGE_RELS.has(e.rel) &&
        !COMPOUND_RELS.has(e.rel) &&
        visibleNodeIds.has(e.source) &&
        visibleNodeIds.has(e.target),
    );

    const parentMap = buildParentMap(topology.edges);
    const positions = computePositions(visibleNodes, topology.edges);

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
      container: ref.current,
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
      // preset keeps positions stable on collapse/expand — our layout
      // deliberately places children inside the parent's natural area.
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

    cy.on("tap", "node", (evt) => {
      const n = evt.target;
      if (api.isExpandable(n)) {
        api.expand(n);
      } else if (n.isParent() && api.isCollapsible(n)) {
        if (evt.target === n) api.collapse(n);
      }
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [topology]);

  return <div ref={ref} className="cy-canvas" />;
}
