import { expect, test } from "@playwright/test";

const APP = "http://localhost:5174";
const stamp = Date.now().toString(36);
const EMAIL = `e2e-${stamp}@example.com`;
const PASSWORD = "e2e-pass-123";

/**
 * Spec §Testing/Frontend customer path:
 * signup → login → browse → add to cart → buy → view order → raise ticket.
 */
test("customer buys a product and raises a ticket", async ({ page }) => {
  // Signup.
  await page.goto(`${APP}/signup`);
  await page.getByLabel("Name").fill("E2E Shopper");
  await page.getByLabel("Email").fill(EMAIL);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign up" }).click();

  // Browse products → open the first in-stock product.
  await page.waitForURL("**/products", { timeout: 15_000 });
  await page.locator('a[href*="/products/"]', { hasText: "In stock" }).first().click();
  await expect(page.getByRole("button", { name: "Add to cart" })).toBeVisible();

  // Add to cart (toast confirms).
  await page.getByRole("button", { name: "Add to cart" }).click();
  await expect(page.locator(".ns-toast-msg", { hasText: "Added to cart." })).toBeVisible();

  // Cart → checkout.
  await page.goto(`${APP}/cart`);
  await page.getByRole("button", { name: "Proceed to checkout" }).click();
  await page.waitForURL("**/checkout");
  await page.getByLabel("Shipping address").fill("221B Baker Street, Mumbai 400001");
  await page.getByRole("button", { name: /^Pay/ }).click();
  await expect(page.getByText("Payment successful")).toBeVisible({ timeout: 30_000 });

  // Order detail.
  await page.getByRole("button", { name: /Track order/ }).click();
  await expect(page.getByText("Shipping address")).toBeVisible();

  // Raise a ticket for the order.
  await page.goto(`${APP}/tickets/new`);
  await page.getByLabel("Subject").fill("E2E damaged item");
  await page.getByLabel("Description").fill("The item arrived damaged, please refund my order.");
  await page.getByRole("button", { name: "Submit ticket" }).click();
  await expect(page.locator(".ns-toast-msg", { hasText: "Ticket raised." })).toBeVisible();
  await expect(page.getByText("The item arrived damaged")).toBeVisible();
});

test("customer login works with the new account", async ({ page }) => {
  await page.goto(`${APP}/login`);
  await page.getByLabel("Email").fill(EMAIL);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL("**/products", { timeout: 15_000 });
  await expect(page.locator('a[href*="/products/"]').first()).toBeVisible();
});
