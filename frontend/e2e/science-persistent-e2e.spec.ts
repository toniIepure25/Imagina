import { test, expect } from "@playwright/test";

const SCIENCE_API = "http://localhost:8000/api/research-science";

test.describe("Science Persistent E2E: Full Workflow", () => {
  const designKey = `e2e-design-${Date.now()}`;
  const simKey = `e2e-sim-${Date.now()}`;
  let designId: number;
  let simRunId: number;

  test("1. create a persistent design", async ({ request }) => {
    const res = await request.post(`${SCIENCE_API}/designs`, {
      data: {
        n_participants: 18,
        n_sessions: 3,
        trials_per_task: 5,
        seed: 42,
        idempotency_key: designKey,
      },
    });
    expect(res.status()).toBe(201);
    const body = await res.json();
    expect(body.id).toBeTruthy();
    expect(body.hash).toBeTruthy();
    designId = body.id;
  });

  test("2. enqueue simulation and observe queued status", async ({
    request,
  }) => {
    const res = await request.post(`${SCIENCE_API}/simulations`, {
      data: {
        scenario_id: "strict_null",
        mode: "unit",
        n_participants: 18,
        base_seed: 42,
        idempotency_key: simKey,
      },
    });
    expect(res.status()).toBe(202);
    const body = await res.json();
    expect(body.id).toBeTruthy();
    expect(body.status).toBe("queued");
    simRunId = body.id;
  });

  test("3. observe queued status on poll", async ({ request }) => {
    const res = await request.get(`${SCIENCE_API}/simulations/${simRunId}`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(["queued", "claimed", "running", "completed"]).toContain(
      body.status
    );
  });

  test("4. idempotent duplicate POST returns same ID", async ({ request }) => {
    const res = await request.post(`${SCIENCE_API}/simulations`, {
      data: {
        scenario_id: "strict_null",
        mode: "unit",
        n_participants: 18,
        base_seed: 42,
        idempotency_key: simKey,
      },
    });
    expect(res.status()).toBe(202);
    const body = await res.json();
    expect(body.id).toBe(simRunId);
  });

  test("5. endpoint registry accessible", async ({ request }) => {
    const res = await request.get(`${SCIENCE_API}/endpoint-registry`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.hash).toBeTruthy();
    expect(Object.keys(body.endpoints).length).toBeGreaterThan(0);
  });

  test("6. oracle computable for strict_null", async ({ request }) => {
    const res = await request.get(`${SCIENCE_API}/oracles/strict_null`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.contrasts).toBeTruthy();
    expect(Object.keys(body.contrasts).length).toBeGreaterThan(0);
  });

  test("7. science page loads", async ({ page }) => {
    await page.goto("/science");
    await expect(page.locator("body")).not.toBeEmpty();
  });

  test("8. research landing loads", async ({ page }) => {
    await page.goto("/research");
    await expect(page.locator("body")).not.toBeEmpty();
  });
});
