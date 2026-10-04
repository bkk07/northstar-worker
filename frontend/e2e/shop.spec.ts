import { expect, test } from "@playwright/test";

// Phase 7 hero: a customer views orders, raises a ticket in the browser,
// and the row reaches the database (read back through the real backend).
test("customer views orders, raises a ticket, and tracks it", async ({
  page,
  request,
}) => {
  await page.goto("/shop/orders?customer_code=C101");
  await expect(page.getByRole("article", { name: "Order ORD-1942" })).toBeVisible();

  await page.getByRole("link", { name: "ORD-1942" }).click();
  await expect(page.getByRole("heading", { name: "Order ORD-1942" })).toBeVisible();

  await page.getByLabel("Subject").fill("E2E cracked screen");
  await page.getByLabel("What happened?").fill("Playwright end-to-end probe ticket.");
  await page.getByRole("button", { name: "Raise ticket" }).click();

  await expect(page.getByRole("heading", { name: "Ticket status" })).toBeVisible();
  await expect(page.getByText("E2E cracked screen")).toBeVisible();
  const ticketCode = page.url().split("/").pop() ?? "";

  const api = await request.get(`http://127.0.0.1:8000/api/shop/tickets/${ticketCode}`);
  expect(api.ok()).toBeTruthy();
  expect((await api.json()).status).toBe("open");
});
