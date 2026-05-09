import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import cytoscape from "cytoscape";
import type { Core, ElementDefinition } from "cytoscape";
import expandCollapse from "cytoscape-expand-collapse";

import type { SavedPositions, TopologyResponse } from "../api";
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

export interface CanvasHandle {
  /** Read every node's current position — used by the Save button. */
  getPositions(): SavedPositions;
}

interface CanvasProps {
  topology: TopologyResponse;
  /** User-saved positions; override the computed layout for matching ids. */
  savedPositions: SavedPositions;
}

export const Canvas = forwardRef<CanvasHandle, CanvasProps>(function Canvas(
  { topology, savedPositions },
  ref,
) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);

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
    }),
    [],
  );

  useEffect(() => {
    if (!containerRef.current) return;

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
    const computed = computePositions(visibleNodes, topology.edges);

    // Saved positions win over computed ones — that's the whole point of
    // the Save button. Unknown ids in savedPositions are ignored silently.
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
  }, [topology, savedPositions]);

  return <div ref={containerRef} className="cy-canvas" />;
});
