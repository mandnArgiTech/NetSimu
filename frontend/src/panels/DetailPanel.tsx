// Right-side detail panel. Welcome state → empty pitch. Selected → tabs.
//
// Tabs (per design doc § 3b):
//   What is this?  — markdown loaded from /api/concept/{id}
//   Live data      — placeholder until M3 (WebSocket counters)
//   Connections    — derived from topology edges (frontend-only)
//   In context     — placeholder until M5 (focused 2-hop diagram)

import { useEffect, useState } from "react";

import { fetchConcept, type Concept, type TopoEdge, type TopoNode } from "../api";
import { conceptIdFor } from "./tooltips";
import { Markdown } from "./Markdown";
import { Connections } from "./Connections";
import { LiveDataTab } from "./LiveDataTab";

type Tab = "what" | "live" | "conns" | "context";

interface DetailPanelProps {
  selected: TopoNode | null;
  nodes: TopoNode[];
  edges: TopoEdge[];
  onSelect: (id: string) => void;
}

export function DetailPanel({ selected, nodes, edges, onSelect }: DetailPanelProps) {
  const [tab, setTab] = useState<Tab>("what");
  const [concept, setConcept] = useState<Concept | null>(null);
  const [conceptError, setConceptError] = useState<string>("");
  // When the user clicks a `concept:foo` cross-link in the body, we load
  // that concept *without* changing the canvas selection. The override
  // takes over until the user picks a different node.
  const [overrideConceptId, setOverrideConceptId] = useState<string | null>(null);

  const conceptId = overrideConceptId ?? (selected ? conceptIdFor(selected) : null);

  useEffect(() => {
    // Reset override + tab when the user changes selection on the canvas.
    setOverrideConceptId(null);
    setTab("what");
  }, [selected?.id]);

  useEffect(() => {
    if (!conceptId) {
      setConcept(null);
      setConceptError("");
      return;
    }
    let cancelled = false;
    fetchConcept(conceptId)
      .then((c) => {
        if (!cancelled) {
          setConcept(c);
          setConceptError("");
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setConcept(null);
          setConceptError(String(err?.message ?? err));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [conceptId]);

  if (!selected) return <WelcomePanel />;

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
          {selected.type_label}
        </div>
        <div className="text-2xl font-semibold">{selected.id}</div>
      </header>

      <nav
        className="flex border-b"
        style={{ borderColor: "var(--border-soft)" }}
      >
        <TabButton active={tab === "what"} onClick={() => setTab("what")}>
          What is this?
        </TabButton>
        <TabButton active={tab === "live"} onClick={() => setTab("live")}>
          Live data
        </TabButton>
        <TabButton active={tab === "conns"} onClick={() => setTab("conns")}>
          Connections
        </TabButton>
        <TabButton active={tab === "context"} onClick={() => setTab("context")}>
          In context
        </TabButton>
      </nav>

      <div
        className="flex-1 overflow-y-auto px-5 py-5 text-base"
        style={{ background: "#ffffff" }}
      >
        {tab === "what" && (
          <WhatTab
            concept={concept}
            error={conceptError}
            onConceptLink={setOverrideConceptId}
            isOverride={overrideConceptId !== null}
            onClearOverride={() => setOverrideConceptId(null)}
            selectedId={selected.id}
          />
        )}
        {tab === "live" && <LiveDataTab node={selected} />}
        {tab === "conns" && (
          <Connections selected={selected} nodes={nodes} edges={edges} onSelect={onSelect} />
        )}
        {tab === "context" && (
          <PlaceholderTab milestone="M5" feature="focused 2-hop diagram + Geneve packet flow" />
        )}
      </div>
    </aside>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex-1 px-3 py-3 text-base"
      style={{
        background: active ? "#ffffff" : "transparent",
        color: active ? "#0f172a" : "var(--text-secondary)",
        fontWeight: active ? 600 : 500,
        borderBottom: active ? "3px solid #1d4ed8" : "3px solid transparent",
        cursor: "pointer",
        border: "none",
      }}
    >
      {children}
    </button>
  );
}

function WhatTab({
  concept,
  error,
  onConceptLink,
  isOverride,
  onClearOverride,
  selectedId,
}: {
  concept: Concept | null;
  error: string;
  onConceptLink: (id: string) => void;
  isOverride: boolean;
  onClearOverride: () => void;
  selectedId: string;
}) {
  if (error) {
    return (
      <p style={{ color: "#b91c1c" }}>
        Could not load concept: {error}
      </p>
    );
  }
  if (!concept) {
    return (
      <p style={{ color: "var(--text-secondary)" }}>Loading…</p>
    );
  }
  return (
    <div>
      {isOverride && (
        <div
          className="mb-4 flex items-center justify-between rounded-md px-3 py-2 text-base"
          style={{ background: "#fef3c7", color: "#92400e" }}
        >
          <span>Showing cross-linked concept (not the selected entity).</span>
          <button
            type="button"
            onClick={onClearOverride}
            className="text-base font-medium underline"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "#92400e",
            }}
          >
            ← back to {selectedId}
          </button>
        </div>
      )}
      <Markdown body={concept.body} onConceptLink={onConceptLink} />
    </div>
  );
}

function PlaceholderTab({
  milestone,
  feature,
}: {
  milestone: string;
  feature: string;
}) {
  return (
    <div
      style={{
        padding: 24,
        background: "#f8fafc",
        borderRadius: 8,
        border: "1px dashed #cbd5e1",
      }}
    >
      <div className="text-xl font-semibold">Coming in {milestone}</div>
      <p className="mt-2 text-base" style={{ color: "var(--text-secondary)" }}>
        This tab will show {feature}.
      </p>
    </div>
  );
}

function WelcomePanel() {
  return (
    <aside
      className="flex h-full flex-col border-l px-6 py-6"
      style={{
        borderColor: "var(--border-soft)",
        background: "var(--bg-panel)",
        width: 480,
        flexShrink: 0,
      }}
    >
      <h2 className="text-2xl font-semibold">Welcome.</h2>
      <p className="mt-3 text-lg" style={{ color: "var(--text-secondary)" }}>
        Hover anything on the topology to see what it is.
      </p>
      <p className="mt-2 text-lg" style={{ color: "var(--text-secondary)" }}>
        Click anything for a deep dive — the explanation, a connections list,
        and (in upcoming milestones) live counters and a focused diagram.
      </p>
      <p className="mt-4 text-base" style={{ color: "var(--text-secondary)" }}>
        Drag nodes to rearrange. Use Save layout in the header to persist.
      </p>
    </aside>
  );
}
