import { expect, test } from "@playwright/test";

// Phase 27: the same report table appears in /evaluation. The global
// setup reseeds (wiping recorded runs), so the spec records its own run
// through the API first, then reads it back through the UI.
test.describe("evaluation", () => {
  test.beforeEach(async ({ request }) => {
    const recorded = await request.post("http://127.0.0.1:8000/api/eval/runs", {
      data: {
        suite: "e2e-probe",
        scenario_count: 1,
        metrics: { scenarios: 1, task_success_rate: 1.0, unsafe_action_rate: 0.0 },
        results: [
          {
            scenario_id: "S5",
            expected_outcome: "BLOCK",
            actual_outcome: "BLOCK",
            outcome_ok: true,
            scores: {},
          },
        ],
        report_md: "# probe",
      },
    });
    expect(recorded.ok()).toBeTruthy();
  });

  test("results show the §26 table with the recorded run", async ({ page }) => {
    await page.goto("/evaluation");
    await expect(page.getByRole("heading", { name: "Evaluation" })).toBeVisible();
    await expect(page.getByText("task_success_rate")).toBeVisible();
    await expect(page.getByText("100.0%")).toBeVisible();
    await expect(page.getByText("S5")).toBeVisible();
    await expect(page.getByText("expected BLOCK, got BLOCK")).toBeVisible();
  });

  test("scenarios list the seeded catalog", async ({ page }) => {
    await page.goto("/evaluation/scenarios");
    await expect(page.getByText("TCK-101", { exact: true })).toBeVisible();
    await expect(page.getByText("S1", { exact: true })).toBeVisible();
  });

  test("comparison deltas two runs", async ({ page }) => {
    await page.goto("/evaluation/comparison");
    await page.getByLabel("Baseline").selectOption({ index: 1 });
    await page.getByLabel("Candidate").selectOption({ index: 1 });
    await expect(page.getByText("+0.000").first()).toBeVisible();
  });
});
