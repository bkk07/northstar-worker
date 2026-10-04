import { defineConfig } from "@playwright/test";

// Phase 7: shop end-to-end. webServer boots the real backend (seeded DB)
// and the Vite dev server; reuse running servers locally when present.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  reporter: "list",
  use: { baseURL: "http://localhost:5173" },
  projects: [{ name: "chromium" }],
  webServer: [
    {
      command: "python -m uvicorn app.main:app --app-dir ../backend --port 8000",
      env: { PYTHONPATH: "..;../common;../backend" },
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "npm run dev -- --port 5173 --strictPort",
      url: "http://localhost:5173/",
      reuseExistingServer: !process.env.CI,
      timeout: 90_000,
    },
  ],
});
