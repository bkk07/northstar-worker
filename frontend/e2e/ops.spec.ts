import { expect, test } from "@playwright/test";

// Phase 8: every ops mutation is doable by a human, idempotency keys are
// honored, validation errors render, and 401 returns to login. The global
// setup reseeds, so fixed seeded entities stay deterministic.
test.describe("ops console", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/ops/login");
    await page.getByLabel("Agent name").fill("e2e-operator");
    await page.getByRole("button", { name: "Log in" }).click();
    await expect(page).toHaveURL(/\/ops\/tickets$/);
  });

  test("queue paginates ten per page", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Ticket queue" })).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(10);
    await expect(page.getByText(/Page 1 of \d+ \(\d+ tickets\)/)).toBeVisible();
    await expect(page.getByRole("link", { name: "TCK-101" })).toBeVisible();
    await page.getByRole("button", { name: "Next" }).click();
    await expect(page.getByText(/Page 2 of \d+/)).toBeVisible();
  });

  test("customer search surfaces look-alikes", async ({ page }) => {
    await page.goto("/ops/customers");
    await page.getByLabel("Search customers").fill("Priya");
    await page.getByRole("button", { name: "Search" }).click();
    await expect(page.getByText("Priya Nair (C105) — priya.nair@example.com")).toBeVisible();
    await expect(page.getByText("Priya Nayar (C106) — priya.nayar@example.com")).toBeVisible();
  });

  test("order lookup shows lines and totals", async ({ page }) => {
    await page.goto("/ops/orders");
    await page.getByLabel("Order code").fill("ORD-1942");
    await page.getByRole("button", { name: "Look up" }).click();
    await expect(page.getByRole("article", { name: "Order ORD-1942" })).toBeVisible();
    await expect(page.getByText(/ProBook Laptop 14/)).toBeVisible();
  });

  test("replacement creates once and replays the duplicate submit", async ({
    page,
    request,
  }) => {
    await page.goto("/ops/tickets/TCK-111");
    const form = page.getByRole("form", { name: "Create replacement" });
    await form.getByLabel("Order code").fill("ORD-1950");
    await form.getByLabel("Item SKU").fill("CB-05");
    await form.getByRole("button", { name: "Review replacement" }).click();
    await page.getByRole("alertdialog", { name: "Confirm replacement" }).waitFor();
    await page.getByRole("button", { name: "Create replacement" }).click();
    await expect(page.getByText(/Replacement .* created\./).first()).toBeVisible();

    // Same form instance, same idempotency key: the replay returns the entity.
    await form.getByRole("button", { name: "Review replacement" }).click();
    await page.getByRole("button", { name: "Create replacement" }).click();
    await expect(page.getByText(/Replacement .* created\./).nth(1)).toBeVisible();

    const orders = await request.get("http://127.0.0.1:8000/api/shop/orders/ORD-1950");
    const itemId = (await orders.json()).items.find(
      (item: { sku: string }) => item.sku === "CB-05",
    ).id;
    const replacements = await request.get(
      `http://127.0.0.1:8000/api/read/replacements?order_item_id=${itemId}`,
    );
    expect(await replacements.json()).toHaveLength(1);
  });

  test("over-paid refund shows the server validation error", async ({ page }) => {
    await page.goto("/ops/tickets/TCK-117");
    const form = page.getByRole("form", { name: "Create refund" });
    await form.getByLabel("Order code").fill("ORD-1956");
    await form.getByLabel("Amount (Rs.)").fill("6000");
    await form.getByRole("button", { name: "Review refund" }).click();
    await page.getByRole("button", { name: "Create refund" }).click();
    await expect(page.getByRole("alert")).toContainText("exceeds amount paid");
  });

  test("note, reply, and status flows complete", async ({ page }) => {
    await page.goto("/ops/tickets/TCK-140");
    await page.getByLabel("Note text").fill("E2E internal note.");
    await page.getByRole("button", { name: "Add note" }).click();
    await expect(page.getByText("Internal note added.")).toBeVisible();

    await page.goto("/ops/tickets/TCK-127");
    await page.getByLabel("Reply text").fill("E2E customer reply.");
    await page.getByRole("button", { name: "Send reply" }).click();
    await expect(page.getByText("Reply sent to the customer.")).toBeVisible();

    await page.goto("/ops/tickets/TCK-128");
    await page.getByLabel("New status").selectOption("resolved");
    await page.getByRole("button", { name: "Change status" }).click();
    await expect(page.getByText("Ticket set to resolved.")).toBeVisible();
  });

  test("logout then deep link returns to login (401)", async ({ page }) => {
    await page.getByRole("button", { name: "Log out" }).click();
    await expect(page.getByRole("heading", { name: "Ops console login" })).toBeVisible();
    await page.goto("/ops/tickets");
    await expect(page).toHaveURL(/\/ops\/login$/);
    await expect(page.getByRole("heading", { name: "Ops console login" })).toBeVisible();
  });
});
