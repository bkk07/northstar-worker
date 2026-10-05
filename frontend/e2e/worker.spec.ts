import { expect, test } from "@playwright/test";

// Phase 26: an operator submits, observes, and inspects without a
// terminal. The runner daemon does not run in e2e, so fresh tasks sit
// pending with an empty timeline and no packet — the spec pins the
// submit-to-inspect loop and the HITL queues, not live execution.
function uniqueTask() {
  return `E2E worker probe ${Date.now()}`;
}

test.describe("worker control center", () => {
  test("operator submits a task and sees it in the queue", async ({ page }) => {
    const text = uniqueTask();
    await page.goto("/worker");
    await expect(page.getByRole("heading", { name: "Worker Control Center" })).toBeVisible();
    await page.getByLabel("New task").fill(text);
    await page.getByRole("button", { name: "Submit task" }).click();
    await expect(page.getByText("Task submitted for execution.")).toBeVisible();
    await expect(page.getByRole("link", { name: new RegExp(text.slice(0, 20)) })).toBeVisible();
  });

  test("task detail shows the empty timeline and the missing packet", async ({ page }) => {
    const text = uniqueTask();
    await page.goto("/worker");
    await page.getByLabel("New task").fill(text);
    await page.getByRole("button", { name: "Submit task" }).click();
    await page.getByRole("link", { name: new RegExp(text.slice(0, 20)) }).click();
    await expect(page).toHaveURL(/\/worker\/tasks\//);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(text.slice(0, 20));
    await expect(page.getByText("No events yet")).toBeVisible();
    await expect(page.getByText(/No evidence packet yet/)).toBeVisible();
    await expect(page.getByText("No memory recorded.")).toBeVisible();
  });

  test("approval and clarification queues render", async ({ page }) => {
    await page.goto("/worker");
    await expect(page.getByText("No approvals waiting.")).toBeVisible();
    await expect(page.getByText("No questions waiting.")).toBeVisible();
  });

  test("environment panel needs an ops session, then reports status", async ({ page }) => {
    await page.goto("/worker/environment");
    await expect(page.getByText(/Log in through Ops first/)).toBeVisible();

    await page.goto("/ops/login");
    await page.getByLabel("Agent name").fill("e2e-worker");
    await page.getByRole("button", { name: "Log in" }).click();
    await expect(page).toHaveURL(/\/ops\/tickets$/);

    await page.goto("/worker/environment");
    await expect(page.getByText("backend:").locator("..")).toContainText("ok");
    await expect(page.getByRole("button", { name: "Arm fault" })).toBeVisible();
  });
});
