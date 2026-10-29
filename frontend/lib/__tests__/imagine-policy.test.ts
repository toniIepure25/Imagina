import { describe, expect, it } from "vitest";
import { ADAPTIVE_TARGETS, DEFAULT_SIGNALS } from "@/lib/imagineScene";
import { buildConditioning } from "@/lib/imagine/conditioning";
import {
  DEFAULT_POLICY,
  DEFAULT_POLICY_MEMORY,
  stepAdaptivePolicy,
  type PolicyMemory,
} from "@/lib/imagine/policy";

const target = ADAPTIVE_TARGETS.find((item) => item.id === "immersion")!;

describe("adaptive policy", () => {
  it("requires hysteresis before intervening", () => {
    const conditioning = buildConditioning(DEFAULT_SIGNALS);
    const first = stepAdaptivePolicy(
      DEFAULT_SIGNALS,
      target,
      conditioning,
      5000,
      DEFAULT_POLICY_MEMORY,
      DEFAULT_POLICY,
      160,
    );
    expect(first.intervention).toBe(false);
    expect(first.memory.windows).toBe(1);

    const second = stepAdaptivePolicy(DEFAULT_SIGNALS, target, conditioning, 5200, first.memory, DEFAULT_POLICY, 160);
    expect(second.intervention).toBe(true);
    expect(second.signals.attention).not.toBe(DEFAULT_SIGNALS.attention);
    expect(Math.abs(second.signals.attention - DEFAULT_SIGNALS.attention)).toBeLessThanOrEqual(
      DEFAULT_POLICY.maxStepPerSecond * 0.16 + 0.0001,
    );
  });

  it("enforces dwell time between interventions", () => {
    const conditioning = buildConditioning(DEFAULT_SIGNALS);
    const memory: PolicyMemory = { windows: 2, lastChangeMs: 5000 };
    const decision = stepAdaptivePolicy(DEFAULT_SIGNALS, target, conditioning, 6000, memory, DEFAULT_POLICY, 160);
    expect(decision.intervention).toBe(false);
    expect(decision.reason).toContain("dwell");
  });

  it("stops on fatigue and holds on low quality", () => {
    const fatigued = stepAdaptivePolicy(
      { ...DEFAULT_SIGNALS, fatigue: 0.9 },
      target,
      buildConditioning({ ...DEFAULT_SIGNALS, fatigue: 0.9 }),
      9000,
      { windows: 4, lastChangeMs: 0 },
      DEFAULT_POLICY,
      160,
    );
    expect(fatigued.safetyStop).toBe("fatigue");
    expect(fatigued.intervention).toBe(false);

    const noisy = stepAdaptivePolicy(
      { ...DEFAULT_SIGNALS, signal_quality: 0.2 },
      target,
      buildConditioning({ ...DEFAULT_SIGNALS, signal_quality: 0.2 }),
      9000,
      { windows: 4, lastChangeMs: 0 },
      DEFAULT_POLICY,
      160,
    );
    expect(noisy.safetyStop).toBe("quality");
    expect(noisy.intervention).toBe(false);
  });

  it("does not intervene inside the deadband", () => {
    const near = { ...DEFAULT_SIGNALS, ...target.target, signal_quality: 0.86 };
    const decision = stepAdaptivePolicy(
      near,
      target,
      buildConditioning(near),
      9000,
      { windows: 4, lastChangeMs: 0 },
      DEFAULT_POLICY,
      160,
    );
    expect(decision.intervention).toBe(false);
    expect(decision.reason).toContain("deadband");
  });
});
