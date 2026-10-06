import { defineConfig } from "@playwright/test";

/**
 * Phase 10 browser tests (spec §Testing/Frontend).
 *
 * Needs the live stack: API :8000, customer-web :5174, support-web :5175
 * against a migrated + seeded Postgres. Chromium only keeps installs small.
 */
export default defineConfig({
  testDir: "./specs",
  timeout: 120_000,
  retries: 0,
  reporter: "list",
  use: {
    trace: "retain-on-failure",
  },
  projects: [
    { name: "customer", testMatch: /customer\.spec\.ts/ },
    { name: "support", testMatch: /support\.spec\.ts/ },
  ],
});
