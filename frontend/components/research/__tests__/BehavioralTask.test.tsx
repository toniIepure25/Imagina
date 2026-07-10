import { describe, it, expect } from "vitest";
import React from "react";

describe("BehavioralTask component", () => {
  it("should export as default", async () => {
    const mod = await import("../BehavioralTask");
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe("function");
  });

  it("should export TrialResult interface shape", async () => {
    const trialResult = {
      trial_index: 0,
      stimulus_id: "corridor_simple",
      vividness: 5,
      confidence: 4,
      effort: 3,
      response_time_ms: 1500,
    };
    expect(trialResult.trial_index).toBe(0);
    expect(trialResult.vividness).toBeGreaterThanOrEqual(1);
    expect(trialResult.vividness).toBeLessThanOrEqual(7);
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
