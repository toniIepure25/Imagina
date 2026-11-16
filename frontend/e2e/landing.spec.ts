import { test, expect } from "@playwright/test";

test.describe("Public landing", () => {
  test("positions ANIMUS without deprecated legacy scores", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /make imagination/i })).toBeVisible();
    await expect(page.getByRole("link", { name: "Open ANIMUS", exact: true })).toBeVisible();
    await expect(page.getByText(/PID \/ IQI/i)).toHaveCount(0);
    await expect(page.getByText(/Simulated EEG-like series/i)).toHaveCount(0);
  });

  test("states the evidence boundary in the first viewport", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/No human CRT data has been collected/i)).toBeVisible();
    await expect(page.getByText(/not a validated measure of imagination ability/i)).toBeVisible();
  });

  test("has one top-level heading and named links", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toHaveCount(1);
    const links = page.locator("a");
    expect(await links.count()).toBeGreaterThan(4);
    for (const link of await links.all()) {
      expect((await link.getAttribute("aria-label")) || (await link.textContent())?.trim()).toBeTruthy();
    }
  });
});
