import { expect, test, type Page, type Route } from "@playwright/test";

const SHA = "a".repeat(64);
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "base64",
);

function job(state: string, manifest: Record<string, unknown> | null = null) {
  return {
    schema: "IMAGINA-DIFFUSION-JOB-v2",
    id: "job-12345678",
    state,
    provider: "remote-diffusion",
    model_slot: "scene-diffusion-v0",
    created_at: "2026-10-25T20:00:00+00:00",
    updated_at: "2026-10-25T20:00:01+00:00",
    error_code: null,
    error_message: null,
    staged: state === "succeeded" ? "encode" : "queued",
    manifest,
  };
}

const manifest = {
  schema: "IMAGINA-DIFFUSION-MANIFEST-v1",
  job_id: "remote-job",
  state: "succeeded",
  model_slot: "scene-diffusion-v0",
  model_hash: "model-sha",
  seed: 42,
  prompt_hash: "prompt-sha",
  conditioning_hash: "conditioning-sha",
  controls: { clarity: 0.6, fog: 0.3 },
  skybox: {
    url: "/animus/imagine/assets/skybox-12345678",
    width: 4096,
    height: 2048,
    sha256: SHA,
  },
  preview: {
    url: "/animus/imagine/assets/preview-12345678",
    width: 1280,
    height: 720,
    sha256: SHA,
  },
  created_at: "2026-10-25T20:00:00+00:00",
  expires_at: "2099-10-26T20:00:00+00:00",
  provenance: { worker: "mock" },
};

async function mockReady(page: Page) {
  await page.route("http://localhost:8000/animus/imagine/capabilities", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        local: { status: "ready", engine: "local-procedural", first_person: true },
        diffusion: {
          status: "ready",
          provider: "remote-diffusion",
          reason: null,
          model_slot: "scene-diffusion-v0",
          consent_required: true,
          max_skybox: { width: 4096, height: 2048 },
          max_preview: { width: 1280, height: 720 },
        },
        claim_ceiling: "L1_BEHAVIORAL_ASSISTED",
      }),
    }),
  );
  await page.route("http://localhost:8000/animus/imagine/jobs", (route: Route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({
        status: 202,
        contentType: "application/json",
        body: JSON.stringify(job("queued")),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ jobs: [job("queued")] }),
    });
  });
  await page.route("http://localhost:8000/animus/imagine/jobs/job-12345678", (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(job("succeeded", manifest)),
    }),
  );
  await page.route("http://localhost:8000/animus/imagine/assets/**", (route: Route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: PNG }),
  );
}

test("diffusion lane requires consent and applies the generated skybox", async ({ page }) => {
  await mockReady(page);
  await page.goto("/animus/imagine", { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: "Diffusion" }).click();
  await page.getByRole("button", { name: "Request skybox" }).click();

  const dialog = page.getByRole("dialog", { name: /Send this request/i });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("raw EEG");
  await page.getByRole("button", { name: /I consent/i }).click();

  await expect(page.getByTestId("diffusion-lane").getByText("Succeeded")).toBeVisible({ timeout: 8000 });
  await page.getByRole("button", { name: "Use diffusion skybox" }).click();
  await expect(page.getByTestId("imagine-stage").getByText("diffusion skybox")).toBeVisible();
  await expect(page.getByText("hybrid skybox")).toBeVisible();

  await page.getByRole("tab", { name: "Provenance" }).click();
  await expect(page.getByTestId("provenance-lens")).toContainText("diffusion-backed skybox");
  await expect(page.getByTestId("provenance-lens")).toContainText("scene-diffusion-v0");
});

test("offline lane downloads the v2 request without calling a worker", async ({ page }) => {
  await page.goto("/animus/imagine", { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: "Diffusion" }).click();
  await expect(page.getByTestId("diffusion-lane")).toContainText("Remote diffusion is disabled");
  await expect(page.getByRole("button", { name: "Request skybox" })).toBeDisabled();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download request" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("imagina-diffusion-request-v2.json");
});
