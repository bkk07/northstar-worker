import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Phase 1 support console (spec §4, §27). Separate app from customer-web.
// Internal staff UI: dashboard shell + ticket shell. No AI yet (Phase 8+).
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: {
    port: 5175,
    proxy: { "/api": process.env.VITE_API_URL ?? "http://127.0.0.1:8000" },
  },
});
