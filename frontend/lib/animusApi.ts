import { apiFetch } from "./api";

// ANIMUS closed-loop imagination amplifier — typed client (ANIMUS-P1).
// Simulated / behavioral only (claim levels L0/L1). No decoded neural content.

export interface AnimusSceneGraph {
  objects: string[];
  attributes: Record<string, string>;
  relations: [string, string, string][];
}

export interface AnimusState {
  session_id: string;
  mode: string;
  controller: string;
  active: boolean;
  iteration: number;
  claim_level: string;
  claim_label: string;
  global_uncertainty: number;
  scene_graph: AnimusSceneGraph;
  n_candidates: number;
  n_events: number;
}

export interface AnimusCandidate {
  candidate_id: string;
  iteration: number;
  visual_embedding: number[];
  scene_graph: AnimusSceneGraph;
  description: string;
  generator: string;
  seed: number;
  modality: string;
  asset_ref: string | null;
}

export interface AnimusEvent {
  seq: number;
  event_type: string;
  timestamp: string;
  iteration: number;
  claim_level: string;
  payload: Record<string, unknown>;
}

export interface AnimusTimeline {
  events: AnimusEvent[];
  uncertainty_series: number[];
}

export interface AnimusFeedback {
  channel: string;
  candidate_id?: string;
  attribute?: string;
  target_option?: string;
  direction?: string;
  object?: string;
  op?: string;
  confidence?: number;
  text?: string;
  closer?: boolean;
  strength?: number;
}

export interface AnimusBelief {
  version: string;
  iteration: number;
  objects: Record<string, number>;
  global_scene_attributes: Record<string, Record<string, number>>;
  global_uncertainty: number;
  confidence_by_component: Record<string, number>;
  evidence_sources: string[];
}

export function createSession(body: {
  mode?: string;
  controller?: string;
  seed?: number;
  max_iterations?: number;
  target_index?: number;
}): Promise<AnimusState> {
  return apiFetch<AnimusState>("/animus/sessions", { method: "POST", body: JSON.stringify(body) });
}

export function generateCandidate(sid: string, n = 1, jitter = 0): Promise<{ candidates: AnimusCandidate[] }> {
  return apiFetch<{ candidates: AnimusCandidate[] }>(`/animus/sessions/${sid}/generate`, {
    method: "POST",
    body: JSON.stringify({ n, jitter }),
  });
}

export function sendFeedback(sid: string, fb: AnimusFeedback): Promise<AnimusState> {
  return apiFetch<AnimusState>(`/animus/sessions/${sid}/feedback`, {
    method: "POST",
    body: JSON.stringify(fb),
  });
}

export function stepSession(sid: string): Promise<AnimusState> {
  return apiFetch<AnimusState>(`/animus/sessions/${sid}/step`, { method: "POST" });
}

export function getState(sid: string): Promise<AnimusState> {
  return apiFetch<AnimusState>(`/animus/sessions/${sid}`);
}

export function getBelief(sid: string): Promise<AnimusBelief> {
  return apiFetch<AnimusBelief>(`/animus/sessions/${sid}/belief`);
}

export function getCandidates(sid: string): Promise<{ candidates: AnimusCandidate[] }> {
  return apiFetch<{ candidates: AnimusCandidate[] }>(`/animus/sessions/${sid}/candidates`);
}

export function getTimeline(sid: string): Promise<AnimusTimeline> {
  return apiFetch<AnimusTimeline>(`/animus/sessions/${sid}/timeline`);
}

export function stopSession(sid: string): Promise<AnimusState> {
  return apiFetch<AnimusState>(`/animus/sessions/${sid}/stop`, { method: "POST" });
}

// The attribute-correction directions the workspace exposes.
export const ATTRIBUTE_DIRECTIONS: { label: string; direction: string }[] = [
  { label: "More blue", direction: "more_blue" },
  { label: "Warmer", direction: "warmer" },
  { label: "Brighter", direction: "brighter" },
  { label: "Darker", direction: "darker" },
  { label: "Less fog", direction: "less_fog" },
  { label: "More detail", direction: "more_detailed" },
  { label: "More depth", direction: "more_depth" },
  { label: "Wider view", direction: "wider" },
  { label: "More motion", direction: "more_motion" },
  { label: "More realistic", direction: "more_realistic" },
];

export const OBJECT_CHOICES = ["castle", "moon", "fog", "tree", "mountain", "water", "star", "bridge"];
