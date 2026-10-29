import { test, expect } from "@playwright/test";

const ROUTES = [
  { path: "/method", heading: "Every number has a source" },
  { path: "/science", heading: "What this instrument can and cannot support" },
  { path: "/research/design", heading: "Design the test before you see the data" },
  { path: "/research/participant", heading: "Three prompts. Three ratings." },
  { path: "/research/operator", heading: "Operator dashboard" },
  { path: "/research/synthetic-demo", heading: "Three-condition engineering run" },
  { path: "/animus/imagine", heading: "Describe a place. Step inside it." },
];

for (const route of ROUTES) {
  test.describe(`instrument route ${route.path}`, () => {
    test("loads without a page error or console exception", async ({ page }) => {
      const errors: string[] = [];
      page.on("pageerror", (error) => errors.push(error.message));
      const response = await page.goto(route.path, { waitUntil: "networkidle" });
      expect(response?.status()).toBeLessThan(400);
      await expect(page.getByRole("heading", { level: 1 })).toContainText(route.heading);
      expect(errors).toEqual([]);
    });

    test("does not overflow the viewport at 390px or 1440px", async ({ page }) => {
      for (const width of [390, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await page.goto(route.path, { waitUntil: "networkidle" });
        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        expect(overflow, `${route.path} overflows at ${width}px`).toBeLessThanOrEqual(1);
      }
    });
  });
}

test("imagine lab rebuilds locally and toggles first person", async ({ page }) => {
  await page.goto("/animus/imagine", { waitUntil: "networkidle" });
  await expect(page.locator('[data-testid="imagine-stage"] canvas')).toBeVisible();
  await expect(page.getByRole("button", { name: "Exit first person" })).toBeVisible();
  await expect(page.getByText("diffusion offline")).toBeVisible();

  const before = await page.getByText(/scene hash .* local only/).innerText();
  await page.locator("#signal-attention").fill("0.91");
  await expect(page.getByText(/scene hash .* local only/)).not.toHaveText(before);

  await page.getByRole("button", { name: "Exit first person" }).click();
  await expect(page.getByRole("button", { name: "Enter first person" })).toBeVisible();

  await page.getByRole("button", { name: "Build preview" }).click();
  await expect(page.getByRole("status").last()).toContainText("No model was called");

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download job spec" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("imagina-diffusion-request-v2.json");
});

test("glass box exposes provenance from a metric", async ({ page }) => {
  await page.goto("/science", { waitUntil: "networkidle" });
  const mark = page.getByRole("button", { name: /Evidence: IQI/i }).first();
  await expect(mark).toBeVisible();
  await mark.click();
  const drawer = page.getByRole("dialog", { name: "IQI" });
  await expect(drawer).toBeVisible();
  await expect(drawer).toContainText("What it cannot show");
  await page.getByRole("button", { name: "Close evidence panel" }).click();
  await expect(drawer).toBeHidden();
});

test("study designer locks a completed plan locally", async ({ page }) => {
  await page.goto("/research/design", { waitUntil: "networkidle" });
  await page.getByLabel("Plan title").fill("Vividness under guided practice");
  await page
    .getByLabel("Question")
    .fill("Does guided practice change self-reported vividness within this single case?");
  await page.getByRole("button", { name: "5 Review & export" }).click();
  await expect(page.getByText("No blocking errors.")).toBeVisible();
  await page.getByRole("button", { name: "Go to lock" }).click();
  await expect(page.getByText(/Locked revision/)).toBeVisible();
});
