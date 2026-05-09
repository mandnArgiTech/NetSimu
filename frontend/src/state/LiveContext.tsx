// Live state store for streamed events.
//
// State shape per entity:
//   - latest: the most recent event payload (kind, ts, counters, state).
//   - samples: a small ring buffer of {ts, bytesIn, bytesOut} for the
//     sparkline. Capped at SAMPLE_LIMIT to keep memory bounded.
//
// We deliberately keep the store flat keyed by entity id so a node-level
// component can pull its own slice with one lookup, no traversal.

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  type ReactNode,
} from "react";

import { connectStream, type StreamEvent, type StreamMessage } from "./connectStream";

const SAMPLE_LIMIT = 60;

export type ConnectionStatus = "connecting" | "connected" | "disconnected";

export interface CounterSample {
  ts: number;
  bytesIn: number;
  bytesOut: number;
  deltaIn: number;
  deltaOut: number;
}

export interface EntityLive {
  latest: StreamEvent;
  samples: CounterSample[];
}

interface LiveState {
  status: ConnectionStatus;
  entities: Record<string, EntityLive>;
}

type Action =
  | { type: "status"; status: ConnectionStatus }
  | { type: "snapshot"; state: Record<string, StreamEvent> }
  | { type: "event"; event: StreamEvent };

const INITIAL: LiveState = {
  status: "connecting",
  entities: {},
};

function reducer(state: LiveState, action: Action): LiveState {
  switch (action.type) {
    case "status":
      return { ...state, status: action.status };

    case "snapshot": {
      const entities: Record<string, EntityLive> = {};
      for (const [id, ev] of Object.entries(action.state)) {
        entities[id] = {
          latest: ev,
          samples: ev.kind === "counters" ? [sampleFrom(ev)] : [],
        };
      }
      return { ...state, entities };
    }

    case "event": {
      const ev = action.event;
      const id = typeof ev.entity === "string" ? ev.entity : null;
      if (!id) return state;
      const prev = state.entities[id] ?? { latest: ev, samples: [] };
      const next: EntityLive = { latest: ev, samples: prev.samples };
      if (ev.kind === "counters") {
        const sample = sampleFrom(ev);
        next.samples = [...prev.samples, sample].slice(-SAMPLE_LIMIT);
      }
      return {
        ...state,
        entities: { ...state.entities, [id]: next },
      };
    }

    default:
      return state;
  }
}

function sampleFrom(ev: StreamEvent): CounterSample {
  return {
    ts: typeof ev.ts === "number" ? ev.ts : Date.now() / 1000,
    bytesIn: typeof ev.bytes_in === "number" ? ev.bytes_in : 0,
    bytesOut: typeof ev.bytes_out === "number" ? ev.bytes_out : 0,
    deltaIn: typeof ev.delta_in === "number" ? ev.delta_in : 0,
    deltaOut: typeof ev.delta_out === "number" ? ev.delta_out : 0,
  };
}

const LiveContext = createContext<LiveState | null>(null);

export function LiveProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, INITIAL);
  // Keep the dispatch in a ref so the stream callback never closes over a stale one.
  const dispatchRef = useRef(dispatch);
  dispatchRef.current = dispatch;

  useEffect(() => {
    const handle = connectStream({
      onMessage: (msg: StreamMessage) => {
        if (msg.type === "snapshot") {
          dispatchRef.current({ type: "snapshot", state: msg.state });
        } else if (msg.type === "event") {
          dispatchRef.current({ type: "event", event: msg.event });
        }
      },
      onStatus: (status) => dispatchRef.current({ type: "status", status }),
    });
    return () => handle.close();
  }, []);

  // Memoize so consumers re-render only when state actually changes.
  const value = useMemo(() => state, [state]);
  return <LiveContext.Provider value={value}>{children}</LiveContext.Provider>;
}

export function useLiveState(): LiveState {
  const ctx = useContext(LiveContext);
  if (!ctx) throw new Error("useLiveState must be used inside <LiveProvider>");
  return ctx;
}

export function useLiveEntity(id: string | null): EntityLive | null {
  const { entities } = useLiveState();
  if (!id) return null;
  return entities[id] ?? null;
}

export function useConnectionStatus(): ConnectionStatus {
  return useLiveState().status;
}
