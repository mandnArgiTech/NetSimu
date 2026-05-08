import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchLayout,
  fetchTopology,
  resetLayout,
  saveLayout,
  type SavedPositions,
  type TopologyResponse,
} from "./api";
import {
  Canvas,
  type CanvasHandle,
  type HoverPayload,
  type Selection,
} from "./topology/Canvas";
import { DetailPanel } from "./panels/DetailPanel";
import { EdgeDetail } from "./panels/EdgeDetail";
import { Tooltip } from "./panels/Tooltip";
import { tooltipFor, tooltipForEdge } from "./panels/tooltips";

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: TopologyResponse };

export default function App() {
  const [topology, setTopology] = useState<LoadState>({ kind: "loading" });
  const [savedPositions, setSavedPositions] = useState<SavedPositions>({});
  const [status, setStatus] = useState<string>("");
  const [statusKind, setStatusKind] = useState<"info" | "error">("info");
  const [selection, setSelection] = useState<Selection | null>(null);
  const [hover, setHover] = useState<HoverPayload | null>(null);
  const [canvasKey, setCanvasKey] = useState(0);

  const canvasRef = useRef<CanvasHandle>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchTopology(), fetchLayout()])
      .then(([topo, saved]) => {
        if (cancelled) return;
        setTopology({ kind: "ready", data: topo });
        setSavedPositions(saved);
      })
      .catch((err) => {
        if (cancelled) return;
        setTopology({ kind: "error", message: String(err?.message ?? err) });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const flash = useCallback((msg: string, kind: "info" | "error" = "info") => {
    setStatus(msg);
    setStatusKind(kind);
    window.setTimeout(() => setStatus(""), 3500);
  }, []);

  const handleSave = useCallback(async () => {
    const positions = canvasRef.current?.getPositions();
    if (!positions) {
      flash("Canvas not ready", "error");
      return;
    }
    try {
      const count = await saveLayout(positions);
      flash(`Saved layout (${count} nodes).`);
    } catch (err) {
      flash(`Save failed: ${(err as Error).message}`, "error");
    }
  }, [flash]);

  const handleReset = useCallback(async () => {
    try {
      await resetLayout();
      setSavedPositions({});
      setCanvasKey((k) => k + 1);
      flash("Layout reset to default.");
    } catch (err) {
      flash(`Reset failed: ${(err as Error).message}`, "error");
    }
  }, [flash]);

  // The Connections list and EdgeDetail's endpoint buttons call this
  // with a peer node id. We both update selection AND ask the canvas to
  // highlight + center it.
  const handleSelectFromPanel = useCallback((id: string) => {
    setSelection({ kind: "node", id });
    canvasRef.current?.selectNode(id);
  }, []);

  const ready = topology.kind === "ready";
  const selectedNode =
    ready && selection?.kind === "node"
      ? topology.data.nodes.find((n) => n.id === selection.id) ?? null
      : null;
  const selectedEdge =
    ready && selection?.kind === "edge"
      ? topology.data.edges.find((e) => e.id === selection.id) ?? null
      : null;

  return (
    <div className="flex h-full flex-col">
      <Header
        stats={ready ? topology.data.stats : undefined}
        savedCount={Object.keys(savedPositions).length}
        canSave={ready}
        onSave={handleSave}
        onReset={handleReset}
        status={status}
        statusKind={statusKind}
      />
      <main className="flex flex-1 overflow-hidden">
        <div className="flex-1 overflow-hidden">
          {topology.kind === "loading" && (
            <CenterMessage text="Loading topology…" />
          )}
          {topology.kind === "error" && (
            <CenterMessage text={`Could not load topology: ${topology.message}`} />
          )}
          {ready && (
            <Canvas
              key={canvasKey}
              ref={canvasRef}
              topology={topology.data}
              savedPositions={savedPositions}
              selection={selection}
              onSelect={setSelection}
              onHover={setHover}
            />
          )}
        </div>
        {ready && selectedEdge ? (
          <EdgeDetail
            edge={selectedEdge}
            nodes={topology.data.nodes}
            onSelectNode={handleSelectFromPanel}
          />
        ) : ready ? (
          <DetailPanel
            selected={selectedNode}
            nodes={topology.data.nodes}
            edges={topology.data.edges}
            onSelect={handleSelectFromPanel}
          />
        ) : null}
      </main>
      <LegendBar />
      {hover && (
        <Tooltip
          text={
            hover.kind === "node"
              ? tooltipFor(hover.node)
              : tooltipForEdge(hover.edge)
          }
          x={hover.pageX}
          y={hover.pageY}
        />
      )}
    </div>
  );
}

interface HeaderProps {
  stats?: Record<string, number>;
  savedCount: number;
  canSave: boolean;
  onSave: () => void;
  onReset: () => void;
  status: string;
  statusKind: "info" | "error";
}

function Header({
  stats,
  savedCount,
  canSave,
  onSave,
  onReset,
  status,
  statusKind,
}: HeaderProps) {
  return (
    <header
      className="flex items-baseline justify-between gap-6 border-b px-6 py-4"
      style={{ borderColor: "var(--border-soft)" }}
    >
      <div className="flex-shrink-0">
        <h1 className="text-3xl font-semibold tracking-tight">NetSimu — VCF Lab</h1>
        <p className="text-base" style={{ color: "var(--text-secondary)" }}>
          Hover for a one-liner. Click for the deep dive. Drag to rearrange.
        </p>
      </div>
      <div className="flex items-center gap-4">
        {status && (
          <span
            role="status"
            className="text-base"
            style={{
              color: statusKind === "error" ? "#b91c1c" : "#15803d",
              fontWeight: 500,
            }}
          >
            {status}
          </span>
        )}
        {stats && (
          <span className="text-base" style={{ color: "var(--text-secondary)" }}>
            {stats.nodes} nodes · {stats.edges} edges
            {savedCount > 0 ? ` · ${savedCount} saved` : ""}
          </span>
        )}
        <button
          type="button"
          onClick={onSave}
          disabled={!canSave}
          className="rounded-md border px-4 py-2 text-base font-medium"
          style={{
            background: "#1d4ed8",
            color: "#ffffff",
            borderColor: "#1d4ed8",
            opacity: canSave ? 1 : 0.5,
            cursor: canSave ? "pointer" : "not-allowed",
          }}
        >
          Save layout
        </button>
        <button
          type="button"
          onClick={onReset}
          className="rounded-md border px-4 py-2 text-base font-medium"
          style={{
            background: "#ffffff",
            color: "#0f172a",
            borderColor: "#cbd5e1",
            cursor: "pointer",
          }}
        >
          Reset
        </button>
      </div>
    </header>
  );
}

function LegendBar() {
  const items: Array<{ label: string; bg: string; border: string }> = [
    { label: "Application", bg: "#e6f4ea", border: "#15803d" },
    { label: "Overlay (NSX)", bg: "#dff5f0", border: "#0d9488" },
    { label: "Physical (host/pNIC)", bg: "#eef2f7", border: "#1e3a8a" },
    { label: "Underlay (switches/BGP)", bg: "#e0ecf6", border: "#1d4ed8" },
  ];
  return (
    <footer
      className="flex flex-wrap items-center gap-6 border-t px-6 py-3"
      style={{ borderColor: "var(--border-soft)" }}
    >
      <span className="text-base font-semibold">Layers:</span>
      {items.map((it) => (
        <span key={it.label} className="flex items-center gap-2 text-base">
          <span
            aria-hidden
            style={{
              display: "inline-block",
              width: 18,
              height: 18,
              background: it.bg,
              border: `2px solid ${it.border}`,
              borderRadius: 4,
            }}
          />
          {it.label}
        </span>
      ))}
    </footer>
  );
}

function CenterMessage({ text }: { text: string }) {
  return (
    <div className="flex h-full items-center justify-center">
      <p className="text-xl" style={{ color: "var(--text-secondary)" }}>
        {text}
      </p>
    </div>
  );
}
