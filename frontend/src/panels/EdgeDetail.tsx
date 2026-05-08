// Right-side detail panel content for an edge selection.
//
// Header: friendly relation label + endpoint pair.
// Body: markdown loaded from /api/concept/{rel} (same loader as nodes).
// Endpoints: two clickable buttons that switch the selection to either
// end of the connection — the same pattern Connections uses for peers.

import { useEffect, useState } from "react";

import { fetchConcept, type Concept, type TopoEdge, type TopoNode } from "../api";
import { Markdown } from "./Markdown";
import { labelForRel, conceptIdForEdge } from "./tooltips";

interface EdgeDetailProps {
  edge: TopoEdge;
  nodes: TopoNode[];
  onSelectNode: (id: string) => void;
}

export function EdgeDetail({ edge, nodes, onSelectNode }: EdgeDetailProps) {
  const [concept, setConcept] = useState<Concept | null>(null);
  const [error, setError] = useState<string>("");
  // Cross-link clicks within the body switch to a different concept page
  // without changing canvas selection — same UX as DetailPanel.
  const [overrideConceptId, setOverrideConceptId] = useState<string | null>(null);

  const baseConceptId = conceptIdForEdge(edge);
  const conceptId = overrideConceptId ?? baseConceptId;

  useEffect(() => {
    setOverrideConceptId(null);
  }, [edge.id]);

  useEffect(() => {
    let cancelled = false;
    fetchConcept(conceptId)
      .then((c) => {
        if (!cancelled) {
          setConcept(c);
          setError("");
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setConcept(null);
          setError(String(err?.message ?? err));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [conceptId]);

  const sourceNode = nodes.find((n) => n.id === edge.source);
  const targetNode = nodes.find((n) => n.id === edge.target);

  return (
    <aside
      className="flex h-full flex-col overflow-hidden border-l"
      style={{
        borderColor: "var(--border-soft)",
        background: "var(--bg-panel)",
        width: 480,
        flexShrink: 0,
      }}
    >
      <header
        className="border-b px-5 py-4"
        style={{ borderColor: "var(--border-soft)" }}
      >
        <div className="text-base" style={{ color: "var(--text-secondary)" }}>
          Connection
        </div>
        <div className="text-2xl font-semibold">{labelForRel(edge.rel)}</div>
        <div
          className="mt-2 text-base"
          style={{
            color: "var(--text-secondary)",
            fontFamily:
              "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
          }}
        >
          {edge.source} → {edge.target}
        </div>
      </header>

      <div
        className="flex-1 overflow-y-auto px-5 py-5 text-base"
        style={{ background: "#ffffff" }}
      >
        <section className="mb-6">
          <h3 className="mb-3 text-xl font-semibold">Endpoints</h3>
          <div className="flex flex-col gap-2">
            <EndpointButton
              label="Source"
              node={sourceNode}
              fallbackId={edge.source}
              onClick={() => onSelectNode(edge.source)}
            />
            <EndpointButton
              label="Target"
              node={targetNode}
              fallbackId={edge.target}
              onClick={() => onSelectNode(edge.target)}
            />
          </div>
        </section>

        <section>
          <h3 className="mb-3 text-xl font-semibold">What is this?</h3>
          {error && (
            <p style={{ color: "#b91c1c" }}>Could not load concept: {error}</p>
          )}
          {!error && !concept && (
            <p style={{ color: "var(--text-secondary)" }}>Loading…</p>
          )}
          {concept && (
            <>
              {overrideConceptId && (
                <div
                  className="mb-4 flex items-center justify-between rounded-md px-3 py-2 text-base"
                  style={{ background: "#fef3c7", color: "#92400e" }}
                >
                  <span>Showing cross-linked concept.</span>
                  <button
                    type="button"
                    onClick={() => setOverrideConceptId(null)}
                    className="text-base font-medium underline"
                    style={{
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      color: "#92400e",
                    }}
                  >
                    ← back to connection
                  </button>
                </div>
              )}
              <Markdown body={concept.body} onConceptLink={setOverrideConceptId} />
            </>
          )}
        </section>
      </div>
    </aside>
  );
}

function EndpointButton({
  label,
  node,
  fallbackId,
  onClick,
}: {
  label: string;
  node: TopoNode | undefined;
  fallbackId: string;
  onClick: () => void;
}) {
  const title = node?.id ?? fallbackId;
  const subtitle = node?.type_label ?? "Unknown";
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center justify-between rounded-md border px-4 py-3 text-left"
      style={{
        background: "#ffffff",
        borderColor: "#cbd5e1",
        cursor: "pointer",
      }}
    >
      <div>
        <div className="text-base" style={{ color: "var(--text-secondary)" }}>
          {label}
        </div>
        <div className="text-lg font-semibold">{title}</div>
        <div className="text-base" style={{ color: "var(--text-secondary)" }}>
          {subtitle}
        </div>
      </div>
      <span style={{ color: "#1d4ed8", fontSize: 18 }}>→</span>
    </button>
  );
}
