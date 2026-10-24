import { apiFetch } from "./api";
import type { FeedbackAction } from "./types";

// Multimodal research command center — typed client for /api/multimodal.
// Sessions are SYNTHETIC or REPLAY simulations; nothing here is a brain measurement.

export type SourceKind = "SYNTHETIC" | "REPLAY" | "REAL_SENSOR";
export type EvidenceClass =
  | "DIRECT_MEASUREMENT"
  | "DERIVED_METRIC"
  | "VALIDATED_ESTIMATE"
  | "EXPERIMENTAL_PROXY"
  | "SUBJECTIVE_REPORT";

export const MODALITIES = ["eeg", "ecg", "eda", "respiration", "fnirs"] as const;
export type RealtimeModality = (typeof MODALITIES)[number];

export const EVIDENCE_LABELS: Record<EvidenceClass, string> = {
  DIRECT_MEASUREMENT: "Direct measurement",
  DERIVED_METRIC: "Derived metric",
  VALIDATED_ESTIMATE: "Research-validated estimate",
  EXPERIMENTAL_PROXY: "Experimental proxy",
  SUBJECTIVE_REPORT: "Subjective report",
};

export const SOURCE_LABELS: Record<SourceKind, string> = {
  SYNTHETIC: "SYNTHETIC",
  REPLAY: "REPLAY",
  REAL_SENSOR: "REAL SENSOR",
};

export interface ProviderDescriptor {
  provider_id: string;
  modality: string;
  source_kind: SourceKind;
  support_level: string;
  realtime: boolean;
  formats: string[];
  requires_package: string | null;
  available: boolean;
  note: string;
}

export interface SessionStatus {
  session_id: string;
  t: number;
  duration_s: number;
  done: boolean;
  controller_state: string;
  mode: string;
  policy: string;
  source_kinds: SourceKind[];
  n_ticks: number;
}

export interface DimensionValue {
  value: number | null;
  uncertainty: number | null;
  evidence: EvidenceClass;
}

export interface Tick {
  t: number;
  block: string;
  controller_state: string;
  delivered: boolean;
  hold_reason: string;
  adaptation_note: string;
  safety: string[];
  applied: Record<string, number | string>;
  confidence: number;
  iqi: number | null;
  dimensions: Record<string, DimensionValue>;
  features: Record<string, Record<string, number | null>>;
  alignment_uncertainty_ms: number | null;
  pid_research_metric: number | null;
  scene: { scene_clarity: number; texture_detail: number; fog_density: number; breathing_cue_strength: number;
    prompt_text: string };
  audio: { guidance_level: number; ambient_level: number; script_id: string };
}

export interface StreamHealth {
  modality: string;
  source_kind: SourceKind;
  sync_method: string;
  connected: boolean;
  nominal_rate_hz: number;
  clock_drift_ppm: number;
  jitter_sd_ms: number;
  alignment_uncertainty_ms: number | null;
  data_age_s: number | null;
  gap_samples: number;
  late_samples: number;
  warnings: string[];
}

export interface SyncHealth {
  streams: Record<string, StreamHealth>;
  n_streams: number;
  all_connected: boolean;
  max_alignment_uncertainty_ms: number | null;
  alignment_note: string;
}

export interface Decision {
  tick: number;
  t: number;
  controller_state: string;
  policy: string;
  policy_version: string;
  delivered: boolean;
  hold_reason: string;
  adaptation_note: string;
  safety_findings: { code: string; severity: string; detail: string }[];
  hash: string;
}

export interface CorridorAction {
  action_id: string;
  delivered: boolean;
  controller_state: string;
  policy_version: string;
  scene: FeedbackAction;
  audio: { guidance_level: number; ambient_level: number; script_id: string };
}

export interface CreateSessionRequest {
  session_id: string;
  modalities: RealtimeModality[];
  duration_s: number;
  seed: number;
  mode: "shadow" | "feedback_research";
  policy: "bounded_rules" | "pid_controller_iqi" | "no_feedback";
  run_to_end: boolean;
}

export type Command = "pause" | "resume" | "emergency_stop" | "report_text" | "discomfort";

const BASE = "/api/multimodal";
const post = (body?: unknown): RequestInit => ({ method: "POST", body: body ? JSON.stringify(body) : undefined });

export const listModalities = () =>
  apiFetch<{ modalities: string[]; providers: ProviderDescriptor[] }>(`${BASE}/modalities`);
export const createSession = (req: CreateSessionRequest) => apiFetch<SessionStatus>(`${BASE}/sessions`, post(req));
export const stepSession = (id: string, n = 1) =>
  apiFetch<{ status: SessionStatus; ticks: Tick[] }>(`${BASE}/sessions/${id}/step?n=${n}`, post());
export const sendCommand = (id: string, action: Command, value: string | number = "") =>
  apiFetch<SessionStatus>(`${BASE}/sessions/${id}/command`, post({ action, value }));
export const getTimeline = (id: string) =>
  apiFetch<{ status: SessionStatus; ticks: Tick[] }>(`${BASE}/sessions/${id}/timeline`);
export const getSync = (id: string) => apiFetch<{ current: SyncHealth }>(`${BASE}/sessions/${id}/sync`);
export const getDecisions = (id: string, limit = 12) =>
  apiFetch<Decision[]>(`${BASE}/sessions/${id}/decisions?limit=${limit}`);
export const getCorridor = (id: string) => apiFetch<CorridorAction>(`${BASE}/sessions/${id}/corridor/latest`);
export const getSummary = (id: string) => apiFetch<Record<string, unknown>>(`${BASE}/sessions/${id}`);
export const verifyReplay = (id: string) =>
  apiFetch<{ reproduced: boolean; n: number; final_hash: string; original_final_hash: string }>(
    `${BASE}/sessions/${id}/replay-verify`, post());
export const listProtocols = () => apiFetch<Record<string, Record<string, unknown>>>(`${BASE}/protocols`);
export const runProtocol = (id: string) =>
  apiFetch<{ protocol: string; scope: string; source_kinds: string[]; result: Record<string, unknown> }>(
    `${BASE}/protocols/${id}/run`, post());
export const getHardwareChecklist = () =>
  apiFetch<{ status: string; scope: string; sections: { name: string; items: { id: string; check: string;
    gating?: boolean }[] }[] }>(`${BASE}/hardware-checklist`);

export function isSimulated(kinds: SourceKind[]): boolean {
  return kinds.length > 0 && !kinds.includes("REAL_SENSOR");
}
