import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Phase 1 customer frontend (spec §4, §27). Separate app from support-web.
// API base comes from VITE_API_URL; /api proxy is a dev convenience only.
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: {
    port: 5174,
    proxy: { "/api": process.env.VITE_API_URL ?? "http://127.0.0.1:8000" },
  },
});
