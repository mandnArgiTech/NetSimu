/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  // Light theme only — CLAUDE.md hard rule. Do not enable dark mode.
  darkMode: "class",
  theme: {
    extend: {
      // CLAUDE.md: body 16px minimum, headings 20-32px. No 11/12/13/14px.
      fontSize: {
        base: ["16px", { lineHeight: "1.55" }],
        lg: ["18px", { lineHeight: "1.55" }],
        xl: ["20px", { lineHeight: "1.45" }],
        "2xl": ["24px", { lineHeight: "1.35" }],
        "3xl": ["28px", { lineHeight: "1.3" }],
        "4xl": ["32px", { lineHeight: "1.25" }],
      },
      colors: {
        // Layer palette from CLAUDE.md: muted blues for physical fabric,
        // teals for overlay, greens for application, red/amber for faults.
        layer: {
          physicalBg: "#eef2f7",
          physicalEdge: "#1e3a8a",
          underlayBg: "#e0ecf6",
          underlayEdge: "#1d4ed8",
          overlayBg: "#dff5f0",
          overlayEdge: "#0d9488",
          appBg: "#e6f4ea",
          appEdge: "#15803d",
        },
      },
    },
  },
  plugins: [],
};
