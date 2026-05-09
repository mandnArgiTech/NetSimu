// Replaces the M3 placeholder in DetailPanel.
//
// For entities the simulator emits counters for (switch_port, pnic, tep,
// vm, esx_host, nsx_edge): show two sparklines (bytes in / bytes out) and
// the latest per-second rate underneath.
//
// For entities that emit heartbeats only (bgp_session, t0, tgw, tep_pair):
// show the current state badge and last-seen timestamp.
//
// For everything else (logical objects like project/vpc/segment/dfw_rule):
// say so explicitly — we don't fake counters for objects that don't have
// them in real life.

import { useLiveEntity, useConnectionStatus, type CounterSample } from "../state/LiveContext";
import type { TopoNode } from "../api";

const COUNTER_TYPES = new Set([
  "switch_port",
  "pnic",
  "tep",
  "vm",
  "esx_host",
  "nsx_edge",
]);

const HEARTBEAT_TYPES = new Set([
  "bgp_session",
  "tep_pair",
  "tier0",
  "transit_gateway",
]);

export function LiveDataTab({ node }: { node: TopoNode }) {
  const status = useConnectionStatus();
  const entity = useLiveEntity(node.id);

  if (status === "disconnected") {
    return (
      <Notice tone="warn" title="Stream disconnected">
        The browser lost its connection to the lab server. Live data is
        paused until it reconnects.
      </Notice>
    );
  }
  if (status === "connecting") {
    return (
      <Notice tone="info" title="Connecting…">
        Waiting for the live event stream from the lab server.
      </Notice>
    );
  }

  if (COUNTER_TYPES.has(node.type)) {
    if (!entity || entity.samples.length === 0) {
      return <Notice tone="info" title="No samples yet">Counters will appear within a second.</Notice>;
    }
    return <CounterView node={node} samples={entity.samples} />;
  }

  if (HEARTBEAT_TYPES.has(node.type)) {
    if (!entity) {
      return <Notice tone="info" title="Waiting for heartbeat">Should appear within a few seconds.</Notice>;
    }
    return <HeartbeatView state={String(entity.latest.state ?? "unknown")} ts={Number(entity.latest.ts ?? 0)} />;
  }

  return (
    <Notice tone="info" title="Logical object">
      <span>
        This entity is a logical NSX object — it doesn't have native data-plane
        counters. To see live traffic, look at the {linkHints(node.type)}.
      </span>
    </Notice>
  );
}

function CounterView({ node, samples }: { node: TopoNode; samples: CounterSample[] }) {
  const last = samples[samples.length - 1];
  const inSeries = samples.map((s) => s.deltaIn);
  const outSeries = samples.map((s) => s.deltaOut);

  return (
    <div className="flex flex-col gap-5">
      <Row
        label="Bytes in / sec"
        rate={last.deltaIn}
        total={last.bytesIn}
        series={inSeries}
        color="#1d4ed8"
      />
      <Row
        label="Bytes out / sec"
        rate={last.deltaOut}
        total={last.bytesOut}
        series={outSeries}
        color="#0d9488"
      />
      <p className="text-base" style={{ color: "var(--text-secondary)" }}>
        {samples.length} sample{samples.length === 1 ? "" : "s"} ·
        {" "}
        last update {fmtAge(last.ts)} ago · entity type{" "}
        <code style={codeStyle}>{node.type}</code>
      </p>
    </div>
  );
}

function HeartbeatView({ state, ts }: { state: string; ts: number }) {
  const ok = state === "ok" || state === "established";
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <span
          aria-hidden
          style={{
            width: 14,
            height: 14,
            borderRadius: 999,
            background: ok ? "#15803d" : "#b91c1c",
          }}
        />
        <span className="text-xl font-semibold">{state}</span>
      </div>
      <p className="text-base" style={{ color: "var(--text-secondary)" }}>
        Last heartbeat {fmtAge(ts)} ago.
      </p>
    </div>
  );
}

function Row({
  label,
  rate,
  total,
  series,
  color,
}: {
  label: string;
  rate: number;
  total: number;
  series: number[];
  color: string;
}) {
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between">
        <span className="text-base font-medium">{label}</span>
        <span className="text-lg font-semibold" style={{ color }}>
          {fmtBytes(rate)}/s
        </span>
      </div>
      <Sparkline series={series} color={color} />
      <div className="mt-1 text-base" style={{ color: "var(--text-secondary)" }}>
        cumulative {fmtBytes(total)}
      </div>
    </div>
  );
}

function Sparkline({ series, color }: { series: number[]; color: string }) {
  const W = 420;
  const H = 64;
  const PAD = 4;
  if (series.length < 2) {
    return (
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="sparkline">
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#e2e8f0" />
      </svg>
    );
  }
  const max = Math.max(...series, 1);
  const stepX = (W - PAD * 2) / (series.length - 1);
  const points = series
    .map((v, i) => {
      const x = PAD + i * stepX;
      const y = H - PAD - (v / max) * (H - PAD * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const area = `M${PAD},${H - PAD} L ${points} L ${W - PAD},${H - PAD} Z`;
  return (
    <svg
      width="100%"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="sparkline"
      style={{ background: "#f8fafc", borderRadius: 6 }}
    >
      <path d={area} fill={color} fillOpacity={0.12} />
      <polyline
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
        points={points}
      />
    </svg>
  );
}

function Notice({
  tone,
  title,
  children,
}: {
  tone: "info" | "warn";
  title: string;
  children: React.ReactNode;
}) {
  const palette =
    tone === "warn"
      ? { bg: "#fef3c7", border: "#f59e0b", fg: "#92400e" }
      : { bg: "#f8fafc", border: "#cbd5e1", fg: "#475569" };
  return (
    <div
      style={{
        padding: 16,
        background: palette.bg,
        border: `1px dashed ${palette.border}`,
        borderRadius: 8,
        color: palette.fg,
      }}
    >
      <div className="text-xl font-semibold">{title}</div>
      <p className="mt-1 text-base">{children}</p>
    </div>
  );
}

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(2)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function fmtAge(ts: number): string {
  const ageSec = Math.max(0, Date.now() / 1000 - ts);
  if (ageSec < 1) return "just now";
  if (ageSec < 60) return `${ageSec.toFixed(0)}s`;
  return `${(ageSec / 60).toFixed(0)}m`;
}

function linkHints(etype: string): string {
  switch (etype) {
    case "nsx_project":
      return "VPCs and segments inside it";
    case "vpc":
      return "segments and the VMs attached to them";
    case "segment":
      return "VMs attached to it";
    case "application":
      return "VMs that consist of it";
    case "dfw_rule":
      return "segments the rule applies to";
    default:
      return "underlying entities";
  }
}

const codeStyle = {
  background: "#f1f5f9",
  padding: "2px 6px",
  borderRadius: 4,
  fontSize: 16,
  fontFamily:
    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
} as const;
