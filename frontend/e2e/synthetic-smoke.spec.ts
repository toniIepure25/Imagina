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

test.describe("Synthetic Workflow E2E", () => {
  test("create study, observe completion, verify export", async ({
    page,
    request,
  }) => {
    const studyId = `e2e-${Date.now()}`;
    const idempotencyKey = `e2e-key-${Date.now()}`;

    const createRes = await request.post(
      "http://localhost:8000/api/synthetic-runtime/studies",
      {
        headers: { "Idempotency-Key": idempotencyKey },
        data: {
          study_id: studyId,
          participant_count: 2,
          seed: 42,
          trials_per_session: 2,
          windows_per_trial: 2,
        },
      }
    );
    expect(createRes.status()).toBe(202);
    const createBody = await createRes.json();
    expect(createBody.run_id).toBeTruthy();
    const runId = createBody.run_id;

    let status = "accepted";
    for (let i = 0; i < 60; i++) {
      const pollRes = await request.get(
        `http://localhost:8000/api/synthetic-runtime/runs/${runId}`
      );
      expect(pollRes.status()).toBe(200);
      const pollBody = await pollRes.json();
      status = pollBody.status;
      if (
        ["completed", "completed_with_failures", "failed"].includes(status)
      ) {
        break;
      }
      await page.waitForTimeout(2000);
    }

    expect(["completed", "completed_with_failures"]).toContain(status);

    const sessionsRes = await request.get(
      `http://localhost:8000/api/synthetic-runtime/runs/${runId}/sessions`
    );
    expect(sessionsRes.status()).toBe(200);
    const sessions = await sessionsRes.json();
    expect(sessions.length).toBeGreaterThan(0);

    await page.goto("/research/synthetic-demo");
    await expect(
      page.getByText("Synthetic engineering validation only")
    ).toBeVisible();
  });

  test("idempotent create returns same run", async ({ request }) => {
    const studyId = `idem-${Date.now()}`;
    const key = `idem-key-${Date.now()}`;

    const r1 = await request.post(
      "http://localhost:8000/api/synthetic-runtime/studies",
      {
        headers: { "Idempotency-Key": key },
        data: { study_id: studyId, participant_count: 2, seed: 1 },
      }
    );
    const r2 = await request.post(
      "http://localhost:8000/api/synthetic-runtime/studies",
      {
        headers: { "Idempotency-Key": key },
        data: { study_id: studyId, participant_count: 2, seed: 1 },
      }
    );

    const b1 = await r1.json();
    const b2 = await r2.json();
    expect(b1.run_id).toBe(b2.run_id);
  });

  test("conflict on different input with same key", async ({ request }) => {
    const studyId = `conf-${Date.now()}`;
    const key = `conf-key-${Date.now()}`;

    await request.post(
      "http://localhost:8000/api/synthetic-runtime/studies",
      {
        headers: { "Idempotency-Key": key },
        data: { study_id: studyId, participant_count: 2, seed: 1 },
      }
    );

    const r2 = await request.post(
      "http://localhost:8000/api/synthetic-runtime/studies",
      {
        headers: { "Idempotency-Key": key },
        data: { study_id: studyId, participant_count: 3, seed: 99 },
      }
    );
    expect(r2.status()).toBe(409);
  });
});
