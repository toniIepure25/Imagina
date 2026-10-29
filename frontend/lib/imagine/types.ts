import type { AdaptiveTarget, ImagineSignals, ImagineStyle } from "@/lib/imagineScene";
import type { Vec3 } from "@/lib/animusStudioApi";

export const CONDITIONING_KEYS = [
  "attention",
  "arousal",
  "valence",
  "vividness",
  "fatigue",
  "confidence",
  "theta",
  "alpha",
  "beta",
  "gamma",
  "hrv",
  "eda",
  "signal_quality",
  "uncertainty",
  "trend",
  "stability",
] as const;

export type ConditioningKey = (typeof CONDITIONING_KEYS)[number];
export type ConditioningSource = "demo" | "scenario" | "replay" | "device";

export type ConditioningVector = Record<ConditioningKey, number>;

export interface ImagineConditioning {
  schema: "IMAGINA-CONDITIONING-v1";
  adapter: "conditioning-v0";
  source: ConditioningSource;
  vector: ConditioningVector;
  vectorHash: string;
}

export interface ImagineControls {
  clarity: number;
  fog: number;
  motion: number;
  saturation: number;
  detail: number;
  glow: number;
  cameraPace: number;
  depthFalloff: number;
}

export interface ImagineBriefV2 {
  prompt: string;
  negativePrompt: string;
  style: ImagineStyle;
  seed: string;
}

export interface ImagineCameraPathPoint {
  position: Vec3;
  target: Vec3;
}

export interface ImagineDiffusionRequest {
  schema: "IMAGINA-DIFFUSION-REQUEST-v2";
  requestId: string;
  brief: {
    prompt: string;
    negative_prompt: string;
    style: ImagineStyle;
    seed: string;
  };
  conditioning: {
    schema: ImagineConditioning["schema"];
    adapter: ImagineConditioning["adapter"];
    source: ConditioningSource;
    vector: ConditioningVector;
    quality: number;
    uncertainty: number;
    trend: number;
    stability: number;
    vector_hash: string;
  };
  controls: Record<keyof ImagineControls, number>;
  camera: {
    mode: "first_person";
    path: ImagineCameraPathPoint[];
    start: Vec3;
    fov: number;
  };
  adaptive: {
    target: AdaptiveTarget["id"];
    hz: number;
  };
  output: {
    skybox: { width: number; height: number };
    preview: { width: number; height: number };
    materials: false;
  };
  provenance: {
    composer_version: string;
    policy_version: string;
    app_version: string;
  };
  boundary: string;
}

export interface ImagineJob {
  schema: "IMAGINA-DIFFUSION-JOB-v2";
  id: string;
  state: "queued" | "running" | "cancelling" | "cancelled" | "succeeded" | "failed";
  provider: string;
  model_slot: string;
  created_at: string;
  updated_at: string;
  error_code: string | null;
  error_message: string | null;
  staged: string | null;
  manifest: ImagineManifest | null;
}

export interface ImagineJobList {
  jobs: ImagineJob[];
}

export interface ImagineManifest {
  schema: "IMAGINA-DIFFUSION-MANIFEST-v1";
  job_id: string;
  state: "succeeded";
  model_slot: string;
  model_hash: string;
  seed: number;
  prompt_hash: string;
  conditioning_hash: string;
  controls: Record<string, number>;
  skybox: ImagineAsset;
  preview: ImagineAsset;
  created_at: string;
  expires_at: string;
  provenance: Record<string, string | number | boolean | null>;
}

export interface ImagineAsset {
  url: string;
  width: number;
  height: number;
  sha256: string;
}

export interface ImagineCapabilities {
  local: {
    status: "ready";
    engine: "local-procedural";
    first_person: boolean;
  };
  diffusion: {
    status: "ready" | "blocked";
    provider: "remote-diffusion";
    reason: string | null;
    model_slot: string;
    consent_required: true;
    max_skybox: { width: number; height: number };
    max_preview: { width: number; height: number };
  };
  claim_ceiling: "L1_BEHAVIORAL_ASSISTED";
}

export interface DiffusionError {
  code: string;
  message: string;
  retryable: boolean;
}

export type ConditioningHistory = ImagineSignals[];
