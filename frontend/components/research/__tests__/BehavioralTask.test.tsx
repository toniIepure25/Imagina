import { describe, it, expect } from "vitest";

describe("ImagerySelfReportTask component", () => {
  it("should export as default", async () => {
    const mod = await import("../ImagerySelfReportTask");
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe("function");
  });

  it("should export SelfReportTrialResult interface shape", async () => {
    const trialResult = {
      trial_index: 0,
      stimulus_id: "corridor_simple",
      vividness: 5,
      confidence: 4,
      effort: 3,
      fixation_onset_ms: 0,
      imagery_onset_ms: 3000,
      image_formed_ms: 8000,
      rating_screen_onset_ms: 8001,
      rating_submission_ms: 12000,
      imagery_formation_latency_ms: 5000,
      rating_completion_latency_ms: 3999,
      fixation_onset_utc: "2026-01-01T00:00:00.000Z",
      imagery_onset_utc: "2026-01-01T00:00:03.000Z",
      image_formed_utc: "2026-01-01T00:00:08.000Z",
      rating_screen_onset_utc: "2026-01-01T00:00:08.001Z",
      rating_submission_utc: "2026-01-01T00:00:12.000Z",
    };
    expect(trialResult.trial_index).toBe(0);
    expect(trialResult.vividness).toBeGreaterThanOrEqual(1);
    expect(trialResult.vividness).toBeLessThanOrEqual(7);
    expect(trialResult.imagery_formation_latency_ms).toBe(5000);
    expect(trialResult.rating_completion_latency_ms).toBe(3999);
  });
});

describe("ConsentGate component", () => {
  it("should export as default", async () => {
    const mod = await import("../ConsentGate");
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe("function");
  });
});

describe("OperatorDashboard component", () => {
  it("should export as default", async () => {
    const mod = await import("../OperatorDashboard");
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe("function");
  });
});
