// Plain fetch wrapper. The backend serves the same origin in production
// (FastAPI mounts the dist bundle), and Vite's dev server proxies /api in dev.

export type Layer = "physical" | "underlay" | "overlay" | "application";

export interface TopoNode {
  id: string;
  type: string;
  layer: Layer;
  vendor: string;
  label: string;
  type_label: string;
  attrs: Record<string, unknown>;
}

export interface TopoEdge {
  id: string;
  source: string;
  target: string;
  rel: string;
  attrs: Record<string, unknown>;
}

export interface TopologyResponse {
  nodes: TopoNode[];
  edges: TopoEdge[];
  stats: Record<string, number>;
}

export async function fetchTopology(): Promise<TopologyResponse> {
  const res = await fetch("/api/topology");
  if (!res.ok) {
    throw new Error(`GET /api/topology failed: ${res.status}`);
  }
  return res.json();
}

// Persisted node positions. The backend stores these under
// ~/.netsimu/web_layout.json (or NETSIMU_LAYOUT_PATH).
export type SavedPositions = Record<string, { x: number; y: number }>;

interface LayoutResponse {
  positions?: SavedPositions;
}

export async function fetchLayout(): Promise<SavedPositions> {
  const res = await fetch("/api/layout");
  if (!res.ok) throw new Error(`GET /api/layout failed: ${res.status}`);
  const body = (await res.json()) as LayoutResponse;
  return body.positions ?? {};
}

export async function saveLayout(positions: SavedPositions): Promise<number> {
  const res = await fetch("/api/layout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ positions }),
  });
  if (!res.ok) throw new Error(`POST /api/layout failed: ${res.status}`);
  const body = (await res.json()) as { count: number };
  return body.count;
}

export async function resetLayout(): Promise<void> {
  const res = await fetch("/api/layout", { method: "DELETE" });
  if (!res.ok) throw new Error(`DELETE /api/layout failed: ${res.status}`);
}

// ── Concept content (M2) ──────────────────────────────────────────────
export interface Concept {
  id: string;
  title: string;
  body: string;
}

export async function fetchConcept(id: string): Promise<Concept> {
  const res = await fetch(`/api/concept/${encodeURIComponent(id)}`);
  if (!res.ok) {
    throw new Error(`GET /api/concept/${id} failed: ${res.status}`);
  }
  return res.json();
}
