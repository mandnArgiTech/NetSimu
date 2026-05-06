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
