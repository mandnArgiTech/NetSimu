// Thin WebSocket client with automatic reconnect.
//
// The lab's stream is a simple one-way feed (server → client), so this
// wrapper only worries about: establishing the connection, parsing JSON
// messages, and reconnecting with exponential backoff if the server
// goes away. Backoff caps at 10s so a long server downtime doesn't
// turn into multi-minute waits.

export type StreamEvent = {
  kind: string;
  entity?: string;
  type?: string;
  ts?: number;
  [k: string]: unknown;
};

export type StreamMessage =
  | { type: "snapshot"; state: Record<string, StreamEvent> }
  | { type: "event"; event: StreamEvent };

export interface StreamHandle {
  close(): void;
}

interface ConnectOptions {
  /** Called for each parsed message from the server. */
  onMessage: (msg: StreamMessage) => void;
  /** Called whenever the open/closed state changes. */
  onStatus: (status: "connecting" | "connected" | "disconnected") => void;
}

const BACKOFF_STEPS_MS = [500, 1000, 2000, 4000, 8000, 10_000];

export function connectStream({ onMessage, onStatus }: ConnectOptions): StreamHandle {
  let ws: WebSocket | null = null;
  let attempt = 0;
  let closed = false;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  const wsUrl = (() => {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}/api/stream`;
  })();

  const open = () => {
    if (closed) return;
    onStatus("connecting");
    ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      attempt = 0;
      onStatus("connected");
    };
    ws.onmessage = (evt) => {
      try {
        const parsed = JSON.parse(evt.data) as StreamMessage;
        onMessage(parsed);
      } catch (err) {
        console.error("[stream] bad JSON from server:", err);
      }
    };
    ws.onerror = () => {
      // onclose follows; the user-visible state changes there.
    };
    ws.onclose = () => {
      onStatus("disconnected");
      ws = null;
      if (closed) return;
      const delay =
        BACKOFF_STEPS_MS[Math.min(attempt, BACKOFF_STEPS_MS.length - 1)];
      attempt += 1;
      reconnectTimer = setTimeout(open, delay);
    };
  };

  open();

  return {
    close() {
      closed = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (ws) {
        ws.close();
        ws = null;
      }
    },
  };
}
