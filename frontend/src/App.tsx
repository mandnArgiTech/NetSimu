import { useEffect, useState } from "react";

import { fetchTopology, type TopologyResponse } from "./api";
import { Canvas } from "./topology/Canvas";

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; data: TopologyResponse };

export default function App() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchTopology()
      .then((data) => {
        if (!cancelled) setState({ kind: "ready", data });
      })
      .catch((err) => {
        if (!cancelled)
          setState({ kind: "error", message: String(err?.message ?? err) });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex h-full flex-col">
      <Header stats={state.kind === "ready" ? state.data.stats : undefined} />
      <main className="flex-1 overflow-hidden">
        {state.kind === "loading" && <CenterMessage text="Loading topology…" />}
        {state.kind === "error" && (
          <CenterMessage text={`Could not load topology: ${state.message}`} />
        )}
        {state.kind === "ready" && <Canvas topology={state.data} />}
      </main>
      <LegendBar />
    </div>
  );
}

function Header({ stats }: { stats?: Record<string, number> }) {
  return (
    <header
      className="flex items-baseline justify-between border-b px-6 py-4"
      style={{ borderColor: "var(--border-soft)" }}
    >
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">NetSimu — VCF Lab</h1>
        <p className="text-base" style={{ color: "var(--text-secondary)" }}>
          Static topology view (Milestone 1). Hover and click come next.
        </p>
      </div>
      {stats && (
        <div
          className="text-base"
          style={{ color: "var(--text-secondary)" }}
          aria-label="topology stats"
        >
          {stats.nodes} nodes · {stats.edges} edges · {stats.esx_host} hosts ·{" "}
          {stats.switch} switches · {stats.vm} VMs
        </div>
      )}
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
