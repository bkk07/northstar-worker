import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

// Phase 9: UI fault surfaces armed through the control plane. Each test
// restores a pristine world afterwards (reset + seed), so armed flags never
// leak into other specs.
const OPERATOR = { Authorization: "Bearer local-operator-token" };

async function arm(request: APIRequestContext, faultType: string, target: string) {
  const armed = await request.post("http://127.0.0.1:8000/api/control/chaos", {
    headers: OPERATOR,
    data: { fault_type: faultType, target, trigger: { nth_call: 1 }, params: {} },
  });
  expect(armed.ok()).toBeTruthy();
}

async function login(page: Page) {
  await page.goto("/ops/login");
  await page.getByLabel("Agent name").fill("e2e-faults");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/ops\/tickets$/);
}

test.describe("ops fault surfaces", () => {
  test.afterEach(async ({ request }) => {
    await request.post("http://127.0.0.1:8000/api/control/reset", { headers: OPERATOR });
    await request.post("http://127.0.0.1:8000/api/control/seed", { headers: OPERATOR });
  });

  test("removed search field hides the input", async ({ page, request }) => {
    await arm(request, "REMOVED_SEARCH_FIELD", "ops.customer_search");
    await login(page);
    await page.goto("/ops/customers");
    await expect(page.getByText("Customer search is unavailable")).toBeVisible();
    await expect(page.getByLabel("Search customers")).toHaveCount(0);
  });

  test("dom drift renames labels and reorders fields", async ({ page, request }) => {
    await arm(request, "DOM_DRIFT", "ops.replacements");
    await login(page);
    await page.goto("/ops/tickets/TCK-111");
    const form = page.getByRole("form", { name: "Create replacement" });
    await expect(form.getByLabel("Order reference")).toBeVisible();
    await expect(form.getByLabel("Stock-keeping code")).toBeVisible();
    const order = await page.evaluate(() =>
      Array.from(document.querySelectorAll("#repl-sku,#repl-order")).map((node) => node.id),
    );
    expect(order).toEqual(["repl-sku", "repl-order"]);
  });

  test("stale rerender remounts the queue", async ({ page, request }) => {
    await arm(request, "STALE_ELEMENT", "ops.replacements");
    await login(page);
    await page.goto("/ops/tickets");
    await expect(page.getByText(/Updated at /).first()).toBeVisible({ timeout: 10_000 });
    const first = await page.getByText(/Updated at /).first().textContent();
    await expect
      .poll(async () => page.getByText(/Updated at /).first().textContent(), {
        timeout: 10_000,
      })
      .not.toBe(first);
  });
});
