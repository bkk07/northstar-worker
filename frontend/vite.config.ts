import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Phase 1 skeleton: blank frontend shells. Backend proxy arrives with
// real API phases; keep direct axios baseURL for now (see axiosClient).
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // BACKEND_URL lets pytest (8001) and e2e (8000) run isolated servers.
      "/api": process.env.BACKEND_URL ?? "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
  } as never,
});
