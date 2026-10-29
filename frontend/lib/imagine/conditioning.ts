import type { ImagineSignals } from "@/lib/imagineScene";
import { fnv1a } from "@/lib/randomization";
import {
  CONDITIONING_KEYS,
  type ConditioningHistory,
  type ConditioningKey,
  type ConditioningSource,
  type ConditioningVector,
  type ImagineConditioning,
  type ImagineControls,
} from "./types";

const ADAPTER = "conditioning-v0" as const;

export function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

export function smoothstep(edge0: number, edge1: number, value: number): number {
  const t = clamp01((value - edge0) / Math.max(1e-6, edge1 - edge0));
  return t * t * (3 - 2 * t);
}

function round(value: number): number {
  return Number(clamp01(value).toFixed(4));
}

function mean(values: number[]): number {
  return values.length ? values.reduce((total, value) => total + value, 0) / values.length : 0;
}

function standardDeviation(values: number[]): number {
  if (values.length < 2) return 0;
  const average = mean(values);
  return Math.sqrt(mean(values.map((value) => (value - average) ** 2)));
}

function signalScore(signals: ImagineSignals): number {
  return clamp01(
    signals.attention * 0.3 +
      signals.valence * 0.2 +
      signals.confidence * 0.25 +
      signals.vividness * 0.15 +
      (1 - signals.fatigue) * 0.1,
  );
}

export function deriveMeta(signals: ImagineSignals, history: ConditioningHistory = []) {
  const window = [...history.slice(-30), signals];
  const recent = window.slice(-5).map(signalScore);
  const older = window.slice(-10, -5).map(signalScore);
  const recentMean = recent.length ? mean(recent) : signalScore(signals);
  const olderMean = older.length ? mean(older) : recentMean;
  const trend = round(0.5 + (recentMean - olderMean) * 1.5);
  const stability = round(1 - standardDeviation(window.map(signalScore)) * 3.2);
  const quality = round(signals.signal_quality);
  const uncertainty = round(0.55 * (1 - signals.confidence) + 0.45 * (1 - quality));
  return { quality, uncertainty, trend, stability };
}

export function vectorFromSignals(signals: ImagineSignals, history: ConditioningHistory = []): ConditioningVector {
  const meta = deriveMeta(signals, history);
  return {
    attention: round(signals.attention),
    arousal: round(signals.arousal),
    valence: round(signals.valence),
    vividness: round(signals.vividness),
    fatigue: round(signals.fatigue),
    confidence: round(signals.confidence),
    theta: round(signals.theta),
    alpha: round(signals.alpha),
    beta: round(signals.beta),
    gamma: round(signals.gamma),
    hrv: round(signals.hrv),
    eda: round(signals.eda),
    signal_quality: meta.quality,
    uncertainty: meta.uncertainty,
    trend: meta.trend,
    stability: meta.stability,
  };
}

function conditioningFingerprint(input: string): string {
  const left = fnv1a(`a|${input}`).toString(16).padStart(8, "0");
  const right = fnv1a(`b|${input}`).toString(16).padStart(8, "0");
  return `${left}${right}`;
}

export function canonicalVector(vector: ConditioningVector): string {
  return CONDITIONING_KEYS.map((key) => `${key}:${round(vector[key]).toFixed(4)}`).join("|");
}

export function conditioningHash(vector: ConditioningVector): string {
  return conditioningFingerprint(`${ADAPTER}|${canonicalVector(vector)}`);
}

export function buildConditioning(
  signals: ImagineSignals,
  history: ConditioningHistory = [],
  source: ConditioningSource = "demo",
): ImagineConditioning {
  const vector = vectorFromSignals(signals, history);
  return {
    schema: "IMAGINA-CONDITIONING-v1",
    adapter: ADAPTER,
    source,
    vector,
    vectorHash: conditioningHash(vector),
  };
}

export function qualityGate(conditioning: ImagineConditioning): { influence: number; hold: boolean } {
  const quality = clamp01(conditioning.vector.signal_quality);
  return {
    influence: smoothstep(0.25, 0.85, quality),
    hold: quality < 0.35,
  };
}

const NEUTRAL_CONTROLS: ImagineControls = {
  clarity: 0.55,
  fog: 0.28,
  motion: 0.4,
  saturation: 0.55,
  detail: 0.55,
  glow: 0.45,
  cameraPace: 0.5,
  depthFalloff: 0.4,
};

export function deriveControls(conditioning: ImagineConditioning): ImagineControls {
  const v = conditioning.vector;
  const gate = qualityGate(conditioning);
  const raw: ImagineControls = {
    clarity: clamp01(0.52 * v.attention + 0.28 * v.signal_quality + 0.2 * (1 - v.fatigue)),
    fog: clamp01(0.12 + 0.66 * v.fatigue + 0.34 * v.theta - 0.28 * v.attention),
    motion: clamp01(0.18 + 0.5 * v.arousal + 0.22 * v.gamma + 0.1 * v.eda),
    saturation: clamp01(0.18 + 0.68 * v.valence + 0.14 * v.vividness),
    detail: clamp01(0.4 * v.attention + 0.35 * v.beta + 0.25 * v.vividness),
    glow: clamp01(0.35 * v.vividness + 0.35 * v.alpha + 0.2 * v.gamma + 0.1 * v.valence),
    cameraPace: clamp01(0.35 + 0.35 * v.arousal + 0.2 * v.beta - 0.2 * v.fatigue),
    depthFalloff: clamp01(
      0.2 + 0.55 * (1 - v.attention) + 0.3 * clamp01(0.12 + 0.66 * v.fatigue + 0.34 * v.theta - 0.28 * v.attention),
    ),
  };
  if (gate.influence >= 0.999) return raw;
  return Object.fromEntries(
    (Object.keys(raw) as Array<keyof ImagineControls>).map((key) => [
      key,
      Number((NEUTRAL_CONTROLS[key] + (raw[key] - NEUTRAL_CONTROLS[key]) * gate.influence).toFixed(4)),
    ]),
  ) as unknown as ImagineControls;
}

export function conditioningMeta(conditioning: ImagineConditioning) {
  return {
    quality: conditioning.vector.signal_quality,
    uncertainty: conditioning.vector.uncertainty,
    trend: conditioning.vector.trend,
    stability: conditioning.vector.stability,
  };
}

export function conditioningValue(conditioning: ImagineConditioning, key: ConditioningKey): number {
  return conditioning.vector[key];
}
