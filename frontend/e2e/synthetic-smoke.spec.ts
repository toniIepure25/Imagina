import { test, expect } from "@playwright/test";

test.describe("Synthetic Runtime Smoke", () => {
  test("synthetic-demo page loads with disclaimer", async ({ page }) => {
    await page.goto("/research/synthetic-demo");
    await expect(
      page.getByText("Synthetic engineering validation only")
    ).toBeVisible();
    await expect(page.getByText("Synthetic Runtime Operator")).toBeVisible();
  });

  test("research landing links to synthetic demo", async ({ page }) => {
    await page.goto("/research");
    const link = page.getByRole("link", { name: /synthetic/i });
    await expect(link).toBeVisible();
  });

  test("legacy session page still loads", async ({ page }) => {
    await page.goto("/session");
    await expect(page.locator("body")).not.toBeEmpty();
  });

  test("replay page still loads", async ({ page }) => {
    await page.goto("/replay");
    await expect(page.locator("body")).not.toBeEmpty();
  });

  test("science page still loads", async ({ page }) => {
    await page.goto("/science");
    await expect(page.locator("body")).not.toBeEmpty();
  });

  test("eeg-validation page still loads", async ({ page }) => {
    await page.goto("/research/eeg-validation");
    await expect(page.locator("body")).not.toBeEmpty();
  });
});
