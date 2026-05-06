import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import type { Core, ElementDefinition } from "cytoscape";

import type { TopologyResponse } from "../api";
import { buildStylesheet } from "./style";
import { computePositions } from "./layout";

// cytoscape-dagre is pinned for M2+ (in-context view, packet-flow paths).
// M1 uses a deterministic preset layout — no plugin registration needed yet.

interface CanvasProps {
  topology: TopologyResponse;
}

export function Canvas({ topology }: CanvasProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);

  useEffect(() => {
    if (!ref.current) return;

    const positions = computePositions(topology.nodes);

    const elements: ElementDefinition[] = [
      ...topology.nodes.map((n) => ({
        data: {
          id: n.id,
          label: n.label,
          type: n.type,
          layer: n.layer,
          vendor: n.vendor,
          type_label: n.type_label,
        },
        position: positions[n.id],
      })),
      ...topology.edges.map((e) => ({
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
      minZoom: 0.15,
      maxZoom: 2.5,
    });
    cyRef.current = cy;
    cy.fit(undefined, 30);

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [topology]);

  return <div ref={ref} className="cy-canvas" />;
}
