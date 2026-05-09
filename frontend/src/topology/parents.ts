// Compound parent map — only host and switch are compound parents in M1.
//
// host  → pnics, teps           (via has_pnic, has_tep)
// switch → switch_ports         (via has_port)
//
// Other "is part of" relationships in the topology (project → vpc, vpc →
// segment, app → vm) are NOT compound in M1 because the user's hierarchy
// puts those entities in their own ranks rather than nested. They'll
// appear as siblings in dedicated rows.

import type { TopoEdge } from "../api";

export function buildParentMap(edges: TopoEdge[]): Map<string, string> {
  const parent = new Map<string, string>();
  for (const e of edges) {
    if (e.rel === "has_port") parent.set(e.target, e.source);
    else if (e.rel === "has_pnic") parent.set(e.target, e.source);
    else if (e.rel === "has_tep") parent.set(e.target, e.source);
  }
  return parent;
}

// Compound types that start collapsed. Click the chip to expand.
export const COLLAPSED_BY_DEFAULT_TYPES = new Set<string>([
  "switch", // hides 32 ports
  "esx_host", // hides 16 pnics + 8 teps
]);
