import { test, expect } from "@playwright/test";

const API = "http://localhost:8000/api/synthetic-runtime";

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

test.describe("Acceptance E2E: Full Synthetic Workflow", () => {
  const studyId = "e2e-accept-001";
  const key = "e2e-accept-key-001";
  let runId: string;

  test("1. create synthetic run", async ({ request }) => {
    const res = await request.post(`${API}/studies`, {
      headers: { "Idempotency-Key": key },
      data: {
        study_id: studyId,
        participant_count: 2,
        seed: 42,
        trials_per_session: 2,
        windows_per_trial: 2,
      },
    });
    expect(res.status()).toBe(202);
    const body = await res.json();
    expect(body.run_id).toBeTruthy();
    runId = body.run_id;
  });

  test("2. poll until completion", async ({ page, request }) => {
    // Get the run id from existing runs
    const runsRes = await request.get(`${API}/runs`);
    const runs = await runsRes.json();
    const run = runs.find(
      (r: { study_id: string }) => r.study_id === studyId
    );
    expect(run).toBeTruthy();
    runId = run.run_id;

    let status = run.status;
    for (let i = 0; i < 90; i++) {
      if (["completed", "completed_with_failures", "failed"].includes(status))
        break;
      await page.waitForTimeout(2000);
      const pollRes = await request.get(`${API}/runs/${runId}`);
      const pollBody = await pollRes.json();
      status = pollBody.status;
    }

    expect(status).toBe("completed");
  });

  test("3. verify exact session count (6)", async ({ request }) => {
    const runsRes = await request.get(`${API}/runs`);
    const runs = await runsRes.json();
    runId = runs.find(
      (r: { study_id: string }) => r.study_id === studyId
    ).run_id;

    const sessRes = await request.get(`${API}/runs/${runId}/sessions`);
    expect(sessRes.status()).toBe(200);
    const sessions = await sessRes.json();
    expect(sessions.length).toBe(6);
  });

  test("4. verify no failures", async ({ request }) => {
    const runsRes = await request.get(`${API}/runs`);
    const runs = await runsRes.json();
    runId = runs.find(
      (r: { study_id: string }) => r.study_id === studyId
    ).run_id;

    const failRes = await request.get(`${API}/runs/${runId}/failures`);
    expect(failRes.status()).toBe(200);
    const failures = await failRes.json();
    expect(failures.length).toBe(0);
  });

  test("5. request export and wait for validation", async ({ request }) => {
    const runsRes = await request.get(`${API}/runs`);
    const runs = await runsRes.json();
    runId = runs.find(
      (r: { study_id: string }) => r.study_id === studyId
    ).run_id;

    const exportRes = await request.post(
      `${API}/runs/${runId}/export?allow_overwrite=true`
    );
    expect(exportRes.status()).toBe(202);
    const exportBody = await exportRes.json();
    expect(exportBody.package_hash).toBeTruthy();
    expect(exportBody.validation.valid).toBe(true);
  });

  test("6. verify export status persisted", async ({ request }) => {
    const exportRes = await request.get(`${API}/exports/${studyId}`);
    expect(exportRes.status()).toBe(200);
    const body = await exportRes.json();
    expect(body.export_ready).toBe(true);
  });

  test("7. run replay for each condition", async ({ request }) => {
    const runsRes = await request.get(`${API}/runs`);
    const runs = await runsRes.json();
    runId = runs.find(
      (r: { study_id: string }) => r.study_id === studyId
    ).run_id;

    const sessRes = await request.get(`${API}/runs/${runId}/sessions`);
    const sessions = await sessRes.json();

    const adaptive = sessions.find(
      (s: { condition: string; status: string }) =>
        s.condition === "adaptive" && s.status === "completed"
    );
    const fixed = sessions.find(
      (s: { condition: string; status: string }) =>
        s.condition === "fixed" && s.status === "completed"
    );
    const yoked = sessions.find(
      (s: { condition: string; status: string }) =>
        s.condition === "yoked" && s.status === "completed"
    );

    expect(adaptive).toBeTruthy();
    expect(fixed).toBeTruthy();
    expect(yoked).toBeTruthy();

    for (const session of [adaptive, fixed, yoked]) {
      const replayRes = await request.post(
        `${API}/runs/${runId}/replay/${session.research_session_id}`
      );
      expect(replayRes.status()).toBe(202);
      const replayBody = await replayRes.json();
      expect(replayBody.match).toBe(true);
      expect(replayBody.replay_hash).toBe(replayBody.original_hash);
    }
  });

  test("8. verify replay persisted and accessible", async ({ request }) => {
    const runsRes = await request.get(`${API}/runs`);
    const runs = await runsRes.json();
    runId = runs.find(
      (r: { study_id: string }) => r.study_id === studyId
    ).run_id;

    const sessRes = await request.get(`${API}/runs/${runId}/sessions`);
    const sessions = await sessRes.json();
    const first = sessions[0];

    const replayStatus = await request.get(
      `${API}/replay/${first.research_session_id}`
    );
    expect(replayStatus.status()).toBe(200);
    const body = await replayStatus.json();
    expect(body.replay_verified).toBe(true);
  });

  test("9. status survives page reload", async ({ page, request }) => {
    const runsRes = await request.get(`${API}/runs`);
    const runs = await runsRes.json();
    runId = runs.find(
      (r: { study_id: string }) => r.study_id === studyId
    ).run_id;

    await page.goto("/research/synthetic-demo");
    await page.reload();

    const afterReload = await request.get(`${API}/runs/${runId}`);
    expect(afterReload.status()).toBe(200);
    const body = await afterReload.json();
    expect(body.status).toBe("completed");
    expect(body.export_ready).toBe(true);
    expect(body.replay_verified).toBe(true);
  });
});

test.describe("Negative E2E Tests", () => {
  test("idempotency conflict with changed input", async ({ request }) => {
    const studyId = `e2e-conflict-001`;
    const key = `e2e-conflict-key-001`;

    await request.post(`${API}/studies`, {
      headers: { "Idempotency-Key": key },
      data: { study_id: studyId, participant_count: 2, seed: 1 },
    });

    const r2 = await request.post(`${API}/studies`, {
      headers: { "Idempotency-Key": key },
      data: { study_id: studyId, participant_count: 3, seed: 99 },
    });
    expect(r2.status()).toBe(409);
  });

  test("abort during active run", async ({ page, request }) => {
    const studyId = `e2e-abort-001`;
    const key = `e2e-abort-key-001`;

    const createRes = await request.post(`${API}/studies`, {
      headers: { "Idempotency-Key": key },
      data: {
        study_id: studyId,
        participant_count: 6,
        seed: 7,
        trials_per_session: 5,
        windows_per_trial: 3,
      },
    });
    expect(createRes.status()).toBe(202);
    const { run_id } = await createRes.json();

    await page.waitForTimeout(2000);

    const abortRes = await request.post(`${API}/runs/${run_id}/abort`);
    expect([200, 409]).toContain(abortRes.status());

    for (let i = 0; i < 60; i++) {
      const pollRes = await request.get(`${API}/runs/${run_id}`);
      const body = await pollRes.json();
      if (["aborted", "completed", "failed"].includes(body.status)) break;
      await page.waitForTimeout(1000);
    }
  });

  test("missing idempotency key rejected", async ({ request }) => {
    const res = await request.post(`${API}/studies`, {
      data: { study_id: "no-key", participant_count: 2, seed: 1 },
    });
    expect(res.status()).toBe(422);
  });

  test("nonexistent run returns 404", async ({ request }) => {
    const res = await request.get(`${API}/runs/nonexistent-run-id`);
    expect(res.status()).toBe(404);
  });

  test("export of incomplete run fails", async ({ request }) => {
    const studyId = `e2e-export-fail-001`;
    const key = `e2e-export-fail-key-001`;

    const createRes = await request.post(`${API}/studies`, {
      headers: { "Idempotency-Key": key },
      data: {
        study_id: studyId,
        participant_count: 2,
        seed: 1,
        trials_per_session: 10,
        windows_per_trial: 5,
      },
    });
    const { run_id } = await createRes.json();

    const exportRes = await request.post(`${API}/runs/${run_id}/export`);
    expect(exportRes.status()).toBe(409);
  });
});
