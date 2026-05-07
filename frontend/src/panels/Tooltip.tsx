// Floating tooltip shown on cytoscape node hover.
//
// We render an absolutely-positioned div in document coordinates. The
// canvas reports renderedPosition (pixels relative to the cytoscape
// container) and we translate that to viewport coords via getBoundingClientRect.
// 200ms appearance delay per design doc § 3a.

interface TooltipProps {
  text: string;
  // Page coordinates (viewport) — already translated by the caller.
  x: number;
  y: number;
}

export function Tooltip({ text, x, y }: TooltipProps) {
  return (
    <div
      role="tooltip"
      style={{
        position: "fixed",
        left: x + 14,
        top: y + 14,
        maxWidth: 360,
        background: "#0f172a",
        color: "#ffffff",
        padding: "10px 14px",
        borderRadius: 8,
        fontSize: 16,
        lineHeight: 1.45,
        pointerEvents: "none",
        zIndex: 1000,
        boxShadow: "0 6px 20px rgba(15, 23, 42, 0.25)",
      }}
    >
      {text}
    </div>
  );
}
