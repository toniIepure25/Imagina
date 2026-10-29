import { DEFAULT_SIGNALS, type ImagineSignals } from "@/lib/imagineScene";
import { clamp01 } from "./conditioning";

export type ImagineScenarioId = "steady" | "drift" | "load" | "settle";

export interface ImagineScenario {
  id: ImagineScenarioId;
  label: string;
  description: string;
}

export const SCENARIO_DURATION_SECONDS = 30;

export const SCENARIOS: ImagineScenario[] = [
  {
    id: "steady",
    label: "Steady",
    description: "Small natural variation around the demo baseline.",
  },
  {
    id: "drift",
    label: "Drift",
    description: "Attention and valence fall while theta rises.",
  },
  {
    id: "load",
    label: "Load",
    description: "Fatigue climbs toward the safety stop; quality falls late.",
  },
  {
    id: "settle",
    label: "Settle",
    description: "Starts loaded, then returns toward a stable baseline.",
  },
];

function wave(elapsed: number, period: number, phase = 0): number {
  return Math.sin((elapsed / period) * Math.PI * 2 + phase);
}

export function scenarioAt(id: ImagineScenarioId, elapsedSeconds: number): ImagineSignals {
  const t = clamp01(elapsedSeconds / SCENARIO_DURATION_SECONDS);
  const base = { ...DEFAULT_SIGNALS };
  const drift = wave(elapsedSeconds, 14);
  const breath = wave(elapsedSeconds, 8, 0.8);

  if (id === "steady") {
    return {
      ...base,
      attention: clamp01(base.attention + drift * 0.03),
      arousal: clamp01(base.arousal + breath * 0.025),
      confidence: clamp01(base.confidence + drift * 0.02),
      signal_quality: 0.88,
    };
  }

  if (id === "drift") {
    return {
      ...base,
      attention: clamp01(base.attention - t * 0.2 + drift * 0.03),
      valence: clamp01(base.valence - t * 0.16),
      vividness: clamp01(base.vividness - t * 0.12),
      theta: clamp01(base.theta + t * 0.2),
      fatigue: clamp01(base.fatigue + t * 0.12),
      confidence: clamp01(base.confidence - t * 0.14),
      signal_quality: 0.84,
    };
  }

  if (id === "load") {
    const qualityDrop = t > 0.72 ? (t - 0.72) / 0.28 : 0;
    return {
      ...base,
      attention: clamp01(base.attention - t * 0.24 + drift * 0.02),
      arousal: clamp01(base.arousal + t * 0.14),
      fatigue: clamp01(base.fatigue + t * 0.64),
      theta: clamp01(base.theta + t * 0.26),
      alpha: clamp01(base.alpha - t * 0.12),
      beta: clamp01(base.beta - t * 0.18),
      hrv: clamp01(base.hrv - t * 0.22),
      eda: clamp01(base.eda + t * 0.3),
      confidence: clamp01(base.confidence - t * 0.24),
      signal_quality: clamp01(0.86 - qualityDrop * 0.5),
    };
  }

  const recovery = 1 - t;
  const loaded = scenarioAt("load", SCENARIO_DURATION_SECONDS);
  return {
    ...base,
    attention: clamp01(loaded.attention + t * 0.2),
    arousal: clamp01(loaded.arousal - t * 0.12),
    fatigue: clamp01(loaded.fatigue - t * 0.58),
    theta: clamp01(loaded.theta - t * 0.24),
    alpha: clamp01(loaded.alpha + t * 0.14),
    beta: clamp01(loaded.beta + t * 0.16),
    hrv: clamp01(loaded.hrv + t * 0.2),
    eda: clamp01(loaded.eda - t * 0.24),
    confidence: clamp01(base.confidence + recovery * 0.02),
    signal_quality: clamp01(0.8 + t * 0.12),
  };
}

export function scenarioLabel(id: ImagineScenarioId): string {
  return SCENARIOS.find((scenario) => scenario.id === id)?.label ?? id;
}
