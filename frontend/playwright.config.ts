import { defineConfig } from "@playwright/test";

// Phase 7-8 end-to-end. globalSetup reseeds a pristine world; webServer
// boots the real backend and the Vite dev server (reused locally).
export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./global-setup.ts",
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
