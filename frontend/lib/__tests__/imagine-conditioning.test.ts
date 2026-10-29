import { describe, expect, it } from "vitest";
import { DEFAULT_SIGNALS } from "@/lib/imagineScene";
import {
  buildConditioning,
  canonicalVector,
  conditioningHash,
  deriveControls,
  qualityGate,
  vectorFromSignals,
} from "@/lib/imagine/conditioning";
import { CONDITIONING_KEYS } from "@/lib/imagine/types";
import { SCENARIO_DURATION_SECONDS, scenarioAt } from "@/lib/imagine/scenarios";

describe("Imagine conditioning", () => {
  it("produces sixteen normalized dimensions and a stable hash", () => {
    const conditioning = buildConditioning(DEFAULT_SIGNALS);
    expect(Object.keys(conditioning.vector)).toHaveLength(16);
    expect(CONDITIONING_KEYS).toHaveLength(16);
    expect(conditioning.vectorHash).toBe(conditioningHash(conditioning.vector));
    expect(conditioning.vectorHash).toMatch(/^[a-f0-9]{16}$/);
    for (const key of CONDITIONING_KEYS) {
      expect(conditioning.vector[key]).toBeGreaterThanOrEqual(0);
      expect(conditioning.vector[key]).toBeLessThanOrEqual(1);
    }
  });

  it("is deterministic and changes when quality changes", () => {
    const first = vectorFromSignals(DEFAULT_SIGNALS);
    const second = vectorFromSignals(DEFAULT_SIGNALS);
    expect(canonicalVector(first)).toBe(canonicalVector(second));
    const lowQuality = vectorFromSignals({ ...DEFAULT_SIGNALS, signal_quality: 0.2 });
    expect(canonicalVector(lowQuality)).not.toBe(canonicalVector(first));
  });

  it("holds influence when signal quality is below the gate", () => {
    const low = buildConditioning({ ...DEFAULT_SIGNALS, signal_quality: 0.2 });
    const high = buildConditioning(DEFAULT_SIGNALS);
    expect(qualityGate(low).hold).toBe(true);
    expect(qualityGate(high).hold).toBe(false);
    expect(deriveControls(low).clarity).toBeCloseTo(0.55, 1);
    expect(deriveControls(high).clarity).toBeGreaterThan(0.45);
  });

  it("changes scene controls with valence and fatigue", () => {
    const warm = deriveControls(buildConditioning({ ...DEFAULT_SIGNALS, valence: 0.9, fatigue: 0.1 }));
    const cool = deriveControls(buildConditioning({ ...DEFAULT_SIGNALS, valence: 0.15, fatigue: 0.7 }));
    expect(warm.saturation).toBeGreaterThan(cool.saturation);
    expect(cool.fog).toBeGreaterThan(warm.fog);
  });

  it("keeps scenario outputs finite and within bounds", () => {
    for (const id of ["steady", "drift", "load", "settle"] as const) {
      const frame = scenarioAt(id, SCENARIO_DURATION_SECONDS);
      for (const value of Object.values(frame)) {
        expect(Number.isFinite(value)).toBe(true);
        expect(value).toBeGreaterThanOrEqual(0);
        expect(value).toBeLessThanOrEqual(1);
      }
    }
    expect(scenarioAt("load", SCENARIO_DURATION_SECONDS).fatigue).toBeGreaterThan(0.78);
    expect(scenarioAt("settle", SCENARIO_DURATION_SECONDS).fatigue).toBeLessThan(0.35);
  });
});
