import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // During `npm run dev`, proxy /api/* to the FastAPI backend so the dev
    // workflow matches production (the bundle is served by FastAPI directly).
    // ws:true makes /api/stream upgrade to a WebSocket through the proxy.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        ws: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: true,
  },
});
