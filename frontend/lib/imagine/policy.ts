import type { AdaptiveTarget, ImagineSignals } from "@/lib/imagineScene";
import { clamp01 } from "./conditioning";
import type { ImagineConditioning } from "./types";

export interface AdaptivePolicyConfig {
  maxStepPerSecond: number;
  deadband: number;
  hysteresisWindows: number;
  minDwellMs: number;
  fatigueStop: number;
  qualityHold: number;
}

export interface PolicyMemory {
  windows: number;
  lastChangeMs: number;
}

export interface AdaptiveDecision {
  signals: ImagineSignals;
  memory: PolicyMemory;
  intervention: boolean;
  reason: string;
  confidence: number;
  coherence: number;
  safetyStop: "fatigue" | "quality" | null;
}

export const DEFAULT_POLICY: AdaptivePolicyConfig = {
  maxStepPerSecond: 0.12,
  deadband: 0.03,
  hysteresisWindows: 2,
  minDwellMs: 2500,
  fatigueStop: 0.78,
  qualityHold: 0.35,
};

export const DEFAULT_POLICY_MEMORY: PolicyMemory = {
  windows: 0,
  lastChangeMs: 0,
};

export function policyCoherence(signals: ImagineSignals, target: AdaptiveTarget): number {
  const values = Object.entries(target.target) as Array<[keyof AdaptiveTarget["target"], number]>;
  const distance =
    values.reduce((total, [key, goal]) => total + Math.abs(clamp01(signals[key]) - goal), 0) / values.length;
  return clamp01(1 - distance);
}

function moveToward(current: number, goal: number, maxDelta: number): number {
  const delta = Math.max(-maxDelta, Math.min(maxDelta, goal - current));
  return clamp01(current + delta);
}

export function stepAdaptivePolicy(
  current: ImagineSignals,
  target: AdaptiveTarget,
  conditioning: ImagineConditioning,
  nowMs: number,
  memory: PolicyMemory = DEFAULT_POLICY_MEMORY,
  config: AdaptivePolicyConfig = DEFAULT_POLICY,
  deltaMs = 160,
): AdaptiveDecision {
  const coherence = policyCoherence(current, target);
  const quality = conditioning.vector.signal_quality;
  const base = {
    signals: current,
    memory,
    intervention: false,
    confidence: clamp01((1 - conditioning.vector.uncertainty) * quality),
    coherence,
    safetyStop: null as AdaptiveDecision["safetyStop"],
  };

  if (current.fatigue >= config.fatigueStop) {
    return { ...base, reason: "Safety hold: fatigue estimate is above the stop threshold.", safetyStop: "fatigue" };
  }
  if (quality < config.qualityHold) {
    return { ...base, reason: "Hold: demo signal quality is below the influence threshold.", safetyStop: "quality" };
  }

  const error =
    (Object.entries(target.target) as Array<[keyof AdaptiveTarget["target"], number]>).reduce(
      (total, [key, goal]) => total + Math.abs(clamp01(current[key]) - goal),
      0,
    ) / Object.keys(target.target).length;

  const windows = error > config.deadband ? memory.windows + 1 : 0;
  if (error <= config.deadband) {
    return {
      ...base,
      memory: { ...memory, windows: 0 },
      reason: "Within the deadband. No intervention.",
    };
  }
  if (windows < config.hysteresisWindows) {
    return {
      ...base,
      memory: { ...memory, windows },
      reason: "Waiting for the target error to persist across two windows.",
    };
  }
  if (memory.lastChangeMs > 0 && nowMs - memory.lastChangeMs < config.minDwellMs) {
    return {
      ...base,
      memory: { ...memory, windows },
      reason: "Minimum dwell time has not elapsed.",
    };
  }

  const seconds = Math.max(0.1, Math.min(0.5, deltaMs / 1000));
  const maxDelta = config.maxStepPerSecond * seconds;
  const next: ImagineSignals = { ...current };
  for (const [key, goal] of Object.entries(target.target) as Array<[keyof AdaptiveTarget["target"], number]>) {
    next[key] = moveToward(current[key], goal, maxDelta);
  }
  next.alpha = moveToward(current.alpha, target.target.valence, maxDelta * 0.35);
  next.theta = moveToward(current.theta, target.target.fatigue, maxDelta * 0.35);
  next.beta = moveToward(current.beta, target.target.attention, maxDelta * 0.35);
  next.gamma = moveToward(current.gamma, target.target.vividness, maxDelta * 0.35);
  next.hrv = moveToward(current.hrv, target.target.confidence, maxDelta * 0.25);
  next.eda = moveToward(current.eda, target.target.arousal, maxDelta * 0.25);
  next.signal_quality = current.signal_quality;

  return {
    ...base,
    signals: next,
    memory: { windows, lastChangeMs: nowMs },
    intervention: true,
    reason: `Applying ${target.label.toLowerCase()} target with a capped ${config.maxStepPerSecond.toFixed(2)}/s step.`,
  };
}
