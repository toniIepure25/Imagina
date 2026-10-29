import { API_URL } from "@/lib/api";

export type Vec3 = [number, number, number];

export interface SceneAttribute {
  value: unknown;
  confidence: number;
  provenance: string;
  locked: boolean;
  renderable: boolean;
  source_text?: string | null;
}

export interface SceneEntity {
  id: string;
  kind: string;
  label: string;
  role: string;
  transform: { position: Vec3; rotation: Vec3; scale: Vec3 };
  attributes: Record<string, SceneAttribute>;
  confidence: number;
  provenance: string;
  locked: boolean;
  visible: boolean;
  parent_id: string | null;
}

export interface SceneRelation {
  subject_id: string;
  relation: string;
  object_id: string;
  confidence: number;
  provenance: string;
}

export interface SceneGraph {
  scene_id: string;
  version: number;
  seed: number;
  title: string;
  version_tag: string;
  entities: SceneEntity[];
  relations: SceneRelation[];
  style: string;
  camera: { position: Vec3; target: Vec3; fov: number; motion: string; speed: number };
  lighting: {
    key: { color: string; intensity: number; direction: Vec3 };
    ambient: { color: string; intensity: number };
    rim: { color: string; intensity: number };
  };
  atmosphere: {
    fog: { color: string; density: number };
    sky: { top: string; horizon: string; bottom: string; stars: number; aurora: boolean };
    weather: string;
    time_of_day: string;
  };
  dynamics: { wind: number; water: number; fire: number; floating: number; pulse: number };
  constraints: Array<{ kind: string; target: string; value: unknown; strength: number; provenance: string }>;
  metadata: Record<string, unknown> & { content_hash?: string; warnings?: string[] };
}

export interface VersionSummary {
  version_id: string;
  number: number;
  branch_id: string;
  parent_version_id: string | null;
  source: string;
  label: string;
  intention: string | null;
  claim_level: string;
  created_at: string;
  content_hash: string;
  entity_count: number;
}

export interface BranchSummary {
  branch_id: string;
  name: string;
  head_version_id: string;
  created_at: string;
  parent_branch_id: string | null;
  fork_version_id: string | null;
  is_active: boolean;
}

export interface StudioCandidate {
  candidate_id: string;
  session_id?: string;
  source_version_id: string;
  variant_index: number;
  scene: SceneGraph;
  diff: SceneDiff;
  notes: string[];
  selected: boolean;
  created_at: string;
}

export interface SceneDiff {
  added: Array<{ entity_id: string; label: string; kind: string }>;
  removed: Array<{ entity_id: string; label: string; kind: string }>;
  changed: Array<{
    scope: string;
    entity_id: string | null;
    label: string;
    path: string;
    before: unknown;
    after: unknown;
    provenance: string;
  }>;
  locked_untouched: string[];
  explanation: string[];
  warnings: string[];
  before_hash: string;
  after_hash: string;
}

export interface StudioCapabilities {
  scene_graph: string;
  renderer: string;
  image_generation: string;
  neural_content: string;
  dream_content: string;
  neural_reconstruction: string;
  network_calls: string;
  uploads: string;
  privacy_scope: string;
  behavioral_profile?: string;
  behavioral_reconstruction?: string;
  adaptive_practice?: string;
  epistemic_interview?: string;
  contrast_observatory?: string;
  clinical_use?: string;
  claim_ceiling: string;
}

export interface StudioSnapshot {
  session_id: string;
  title: string;
  intention: string;
  mode: string;
  status: string;
  seed: number;
  privacy_scope: string;
  claim_level: string;
  claim_label: string;
  claim_ceiling: string;
  unauthorized_claims: string[];
  capabilities: StudioCapabilities;
  active_branch_id: string;
  active_branch_name: string;
  active_version_id: string;
  scene: SceneGraph;
  version: VersionSummary;
  diff: SceneDiff;
  branches: BranchSummary[];
  history: VersionSummary[];
  candidates: StudioCandidate[];
  warnings: string[];
  has_undo: boolean;
  has_redo: boolean;
  last_event_seq?: number;
  created_at: string;
  updated_at: string;
  generated?: StudioCandidate[] | null;
  source_version_id?: string | null;
  active_locks?: string[] | null;
  needs_clarification?: boolean | null;
  clarification?: string | null;
  resolutions?: string[] | null;
  parse_warnings?: string[] | null;
  applied?: number | null;
}

export interface StudioIntentSnapshot extends StudioSnapshot {
  needs_clarification: boolean;
  clarification: string | null;
  resolutions: string[];
  parse_warnings: string[];
  applied: number;
}

export interface StudioCommandsSnapshot extends StudioSnapshot {
  applied: number;
  warnings: string[];
}

export interface StudioRegenerateSnapshot extends StudioSnapshot {
  generated: StudioCandidate[];
  source_version_id: string;
  active_locks: string[];
}

export interface StudioVersionDetail extends VersionSummary {
  scene: SceneGraph;
  commands: SceneCommand[];
  diff: SceneDiff;
  generator: string;
}

export interface StudioHistory {
  session_id: string;
  active_branch_id: string;
  branches: BranchSummary[];
  versions: VersionSummary[];
  has_undo: boolean;
  has_redo: boolean;
}

export interface StudioEvent {
  seq: number;
  session_id: string;
  event_type: string;
  version_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface StudioEventsResponse {
  session_id: string;
  events: StudioEvent[];
  has_more: boolean;
}

export interface ProfileDimension {
  id: string;
  label: string;
  description: string;
  construct: string;
  estimate: number | null;
  uncertainty: number;
  n: number;
  reliability: number;
  status: "no_evidence" | "collecting" | "provisional" | "moderate_evidence" | string;
  brier_score?: number | null;
  provenance: string;
}

export interface ErrorSignature {
  n: number;
  omissions: number;
  intrusions: number;
  mean_spatial_error: number | null;
  spatial_n: number;
  epistemic_n?: number;
}

export interface EpistemicProfileSummary {
  n_interviews: number;
  n_probes: number;
  mean_brier: number | null;
  overconfidence: number | null;
  abstention_rate: number | null;
  mean_information_gain: number | null;
  last_interview_id: string | null;
}

export interface ContrastProfileSummary {
  n_sessions: number;
  n_completed: number;
  n_trials: number;
  median_threshold: number | null;
  mean_dprime: number | null;
  mean_brier: number | null;
  calibration_n: number;
  last_contrast_id: string | null;
}

export interface StudioProfile {
  profile_id: string;
  profile_version: string;
  claim_level: string;
  privacy_scope: string;
  trial_count: number;
  dimensions: ProfileDimension[];
  error_signature?: ErrorSignature;
  epistemic?: EpistemicProfileSummary;
  contrast?: ContrastProfileSummary;
  limitations: string[];
  created_at?: string | null;
  updated_at?: string | null;
  measured_at: string;
}

export interface PracticeOption {
  id: string;
  label: string;
  value?: unknown;
  scene?: SceneGraph;
}

export interface PracticeToken {
  token_id: string;
  kind: string;
  label: string;
  role: string;
  color?: string | null;
}

export interface PracticeLayout {
  width: number;
  height: number;
  grid: number;
  tolerance: number;
}

export interface PracticePlacement {
  token_id: string;
  x: number;
  z: number;
}

export type PracticeResponse =
  | { option_id: string }
  | { selected_token_ids: string[] }
  | { placements: PracticePlacement[] };

export interface PracticeTask {
  task_id: string;
  task_type: string;
  dimension: string;
  prompt: string;
  options: PracticeOption[];
  difficulty: number;
  task_seed: number;
  preview_seconds: number;
  response_kind: "option" | "token_selection" | "spatial_placement";
  tokens: PracticeToken[];
  layout?: PracticeLayout | null;
}

export interface PracticeAdaptive {
  dimension: string;
  task_type: string;
  difficulty: number;
  reason: string;
  expected_gain?: number | null;
  trial_index?: number | null;
}

export interface PracticeStart {
  session_id: string;
  source_version_id: string;
  task: PracticeTask;
  adaptive: PracticeAdaptive;
  profile: StudioProfile;
  claim_level: string;
}

export interface PracticeTrial {
  trial_id?: string | null;
  session_id?: string | null;
  client_trial_id?: string | null;
  task_type?: string | null;
  dimension?: string | null;
  difficulty?: number | null;
  task_family?: string | null;
  response_kind?: string | null;
  scoring_version?: string | null;
  stimulus: Record<string, unknown>;
  response: Record<string, unknown>;
  outcome: Record<string, unknown>;
  error_profile?: Record<string, unknown>;
  confidence?: number | null;
  latency_ms?: number | null;
  created_at?: string | null;
}

export interface PracticeSubmit {
  session_id: string;
  trial?: PracticeTrial | null;
  idempotent: boolean;
  feedback?: {
    correct?: boolean;
    correct_option_id?: string | null;
    correct_option_label?: string;
    error_profile?: Record<string, unknown>;
    message?: string;
  } | null;
  next_task?: PracticeTask | null;
  adaptive?: PracticeAdaptive | null;
  profile: StudioProfile;
  last_event_seq: number;
}

export interface EpistemicOption {
  id: string;
  label: string;
}

export interface EpistemicProbe {
  probe_id: string;
  task_id: string;
  probe_type: "object_presence" | "spatial_relation" | string;
  prompt: string;
  options: EpistemicOption[];
  dimension: string;
  difficulty: number;
  preview_seconds: number;
}

export interface StudioInterview {
  interview_id: string;
  session_id: string;
  source_version_id: string;
  protocol_version: string;
  form_id: string;
  difficulty: number;
  status: "active" | "completed" | "abandoned" | string;
  probe_count: number;
  max_probes: number;
  created_at?: string | null;
  completed_at?: string | null;
}

export interface EpistemicObject {
  label: string;
  kind: string;
  probability: number;
  status: string;
}

export interface EpistemicRelation {
  subject: string;
  relation: string;
  object: string;
  probability: number;
  status: string;
}

export interface EpistemicReconstruction {
  objects: EpistemicObject[];
  relations: EpistemicRelation[];
  uncertainty: {
    object_entropy: number;
    relation_entropy: number;
  };
  scores: {
    n_probes: number;
    n_answered: number;
    object_accuracy: number | null;
    spatial_accuracy: number | null;
    mean_brier: number | null;
    coverage: number;
    abstention_rate: number;
    overconfidence: number | null;
    mean_information_gain: number | null;
  };
  protocol_version: string;
  scoring_version: string;
}

export interface InterviewStart {
  session_id: string;
  interview: StudioInterview;
  probe: EpistemicProbe;
  profile: StudioProfile;
  claim_level: string;
}

export interface InterviewSubmit {
  session_id: string;
  interview?: StudioInterview | null;
  trial?: PracticeTrial | null;
  idempotent: boolean;
  feedback?: {
    correct?: boolean | null;
    error_profile?: Record<string, unknown>;
    message?: string;
  } | null;
  next_probe?: EpistemicProbe | null;
  reconstruction?: EpistemicReconstruction | null;
  profile: StudioProfile;
  last_event_seq: number;
}

export interface InterviewSummary {
  session_id: string;
  interview: StudioInterview;
  reconstruction: EpistemicReconstruction;
  profile: StudioProfile;
  claim_level: string;
}

export interface InterviewList {
  session_id: string;
  interviews: StudioInterview[];
}

export interface StudioContrast {
  contrast_id: string;
  session_id: string;
  source_version_id: string;
  protocol_version: string;
  form_id: string;
  max_trials: number;
  difficulty: number;
  occasion: "baseline" | "follow_up" | string;
  delay_hours: number | null;
  status: "active" | "completed" | "abandoned" | string;
  trial_count: number;
  reflection: { strategies?: string[]; notes?: string };
  created_at?: string | null;
  completed_at?: string | null;
}

export interface ContrastOption {
  id: "a" | "b" | string;
  label: string;
  scene: SceneGraph;
}

export interface ContrastTrial {
  trial_id: string;
  task_id: string;
  trial_index: number;
  prompt: string;
  options: ContrastOption[];
  preview_seconds: number;
}

export interface ContrastThreshold {
  threshold: number | null;
  slope: number | null;
  ci: number[] | null;
  censored: boolean | null;
  n: number;
  status: string;
  scoring_version: string;
}

export interface ContrastCalibration {
  n: number;
  brier: number | null;
  overconfidence: number | null;
  type2_auc: number | null;
}

export interface ContrastResult {
  protocol_version: string;
  scoring_version: string;
  n_trials: number;
  n_answered: number;
  coverage: number | null;
  dprime: number | null;
  side_bias: number | null;
  thresholds: Record<string, ContrastThreshold>;
  calibration: ContrastCalibration;
  notes: string[];
}

export interface ContrastStart {
  session_id: string;
  contrast: StudioContrast;
  trial: ContrastTrial;
  profile: StudioProfile;
  claim_level: string;
}

export interface ContrastSubmit {
  session_id: string;
  contrast: StudioContrast;
  trial: Record<string, unknown>;
  recorded: boolean;
  idempotent?: boolean;
  next_trial?: ContrastTrial | null;
  result?: ContrastResult | null;
  profile: StudioProfile;
  last_event_seq?: number;
}

export interface ContrastSummary {
  session_id: string;
  contrast: StudioContrast;
  result: ContrastResult;
  profile: StudioProfile;
  claim_level: string;
}

export interface ContrastList {
  session_id: string;
  contrasts: StudioContrast[];
}

export interface EvidenceSource {
  probe_id: string;
  probe_type: string;
  choice: string;
  confidence: number | null;
  abstained: boolean;
  information_gain: number | null;
  created_at?: string | null;
}

export interface EvidenceItem {
  variable_id: string;
  label: string;
  probe_type: string;
  provenance: "direct_probe" | "prior" | "abstained" | "mixed" | string;
  posterior: number;
  uncertainty: number;
  n_sources: number;
  leave_one_out_delta: number;
  dependence_group: string;
  sources: EvidenceSource[];
}

export interface ObservatoryReliability {
  status: "estimated" | "insufficient" | string;
  reason?: string | null;
  n_occasions: number;
  n_features?: number;
  r: number | null;
  r_ci: number[] | null;
  sem: number | null;
  mdc95: number | null;
  mean_change: number | null;
  dprime_change?: number | null;
  occasions?: Array<{
    contrast_id: string;
    occasion: string;
    form_id: string;
    completed_at?: string | null;
    dprime: number | null;
    thresholds: Record<string, ContrastThreshold>;
  }>;
}

export interface Observatory {
  session_id: string;
  source_version_id: string;
  scene_hash: string;
  belief: EpistemicReconstruction;
  evidence: EvidenceItem[];
  discrimination: ContrastResult | { status: string; reason?: string };
  reliability: ObservatoryReliability;
  boundaries: string[];
  claim_level: string;
}

export interface StudioProtocol {
  protocol_id: string;
  version: string;
  name: string;
  description: string;
  builtin: boolean;
  total_trials: number;
  max_minutes: number;
  dimensions: string[];
}

export interface StudioProtocolList {
  protocol_version: string;
  protocols: StudioProtocol[];
}

export interface StudioHealth {
  status: string;
  system: string;
  product: string;
  schema_version: number;
  claim_level: string;
  claim_label: string;
  claim_ceiling: string;
  unauthorized_claims: string[];
  capabilities: StudioCapabilities;
  journal_mode?: string | null;
  synchronous?: number | null;
  foreign_keys?: boolean | null;
  event_count?: number | null;
  integrity?: string | null;
  foreign_key_violations?: number | null;
}

export interface StudioCapabilitiesResponse {
  claim_level: string;
  claim_label: string;
  claim_ceiling: string;
  unauthorized_claims: string[];
  capabilities: StudioCapabilities;
}

export interface StudioSessionList {
  sessions: SessionSummary[];
}

export interface StudioWorldList {
  worlds: StudioWorld[];
}

export interface StudioDeleteResult {
  deleted: string;
}

export interface StudioWorldSaveResult extends StudioWorld {
  source_session_id: string;
  items: StudioWorldItem[];
}

export interface StudioCreateInput {
  title: string;
  intention: string;
  seed?: number;
}

export interface StudioRegenerateOptions {
  count?: number;
  strength?: number;
  seed?: number;
  locks?: string[];
  preserveUserEdits?: boolean;
  varyCamera?: boolean;
}

export interface StudioBranchInput {
  name?: string;
  from_version_id?: string;
}

export interface StudioWorldInput {
  name: string;
  description?: string;
}

export interface AddEntityCommand {
  op: "add_entity";
  kind: string;
  label?: string;
  position?: Vec3;
  role?: string;
  attributes?: Record<string, unknown>;
}

export interface RemoveEntityCommand {
  op: "remove_entity";
  entity_id: string;
}

export interface SetEntityAttributeCommand {
  op: "set_entity_attribute";
  entity_id: string;
  path: string;
  value: unknown;
  lock?: boolean | null;
}

export interface SetEntityTransformCommand {
  op: "set_entity_transform";
  entity_id: string;
  position?: Vec3;
  rotation?: Vec3;
  scale?: Vec3;
}

export interface LockCommand {
  op: "lock";
  path?: string;
  entity_id?: string | null;
  locked?: boolean;
}

export interface SetSceneAttributeCommand {
  op: "set_scene_attribute";
  path: string;
  value: unknown;
}

export interface SetRelationCommand {
  op: "set_relation";
  subject_id: string;
  relation: string;
  object_id: string;
}

export interface RemoveRelationCommand {
  op: "remove_relation";
  subject_id: string;
  relation: string;
  object_id: string;
}

export type StudioSceneCommand =
  | AddEntityCommand
  | RemoveEntityCommand
  | SetEntityAttributeCommand
  | SetEntityTransformCommand
  | LockCommand
  | SetSceneAttributeCommand
  | SetRelationCommand
  | RemoveRelationCommand;

export interface StudioCommandsPayload {
  commands: StudioSceneCommand[];
  source_text: string;
}

export type StudioWebSocketMessage =
  | { type: "snapshot"; session: StudioSnapshot }
  | { type: "event"; event_type: string; seq?: number; [key: string]: unknown }
  | { type: "resync_required"; reason?: string }
  | { type: "pong" }
  | { type: "error"; code: string; message?: string };

export type StudioWebSocketCommand =
  | { type: "ping" }
  | { type: "intent"; text: string; expected_version_id?: string };

export interface StudioWorldItem {
  item_id: string;
  world_id: string;
  label: string;
  kind: string;
  scene: SceneEntity;
  created_at: string;
}

export interface StudioWorld {
  world_id: string;
  name: string;
  description: string;
  scene: SceneGraph;
  created_at: string;
  source_session_id?: string;
  items?: StudioWorldItem[];
}

export interface SessionSummary {
  session_id: string;
  title: string;
  intention: string;
  status: string;
  seed: number;
  claim_level: string;
  created_at: string;
  updated_at: string;
}

export interface StudioErrorBody {
  detail?: string | Array<{ msg?: string }> | { detail?: string; code?: string };
  code?: string;
}

export class StudioApiError extends Error {
  status: number;
  detail: string;
  code: string;
  retryable: boolean;

  constructor(status: number, detail: string, code = "request_failed") {
    super(detail);
    this.name = "StudioApiError";
    this.status = status;
    this.detail = detail;
    this.code = code;
    this.retryable = status === 0 || status === 503 || status === 409;
  }
}

export interface StudioRequestOptions {
  expectedVersion?: string;
  signal?: AbortSignal;
  timeoutMs?: number;
}

function combineSignals(timeoutMs: number, external?: AbortSignal): {
  signal: AbortSignal;
  cleanup: () => void;
} {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const onAbort = () => controller.abort();
  if (external) {
    if (external.aborted) controller.abort();
    else external.addEventListener("abort", onAbort, { once: true });
  }
  return {
    signal: controller.signal,
    cleanup: () => {
      clearTimeout(timeout);
      external?.removeEventListener("abort", onAbort);
    },
  };
}

async function request<T>(
  path: string,
  init?: RequestInit,
  options: StudioRequestOptions = {},
): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (options.expectedVersion) headers.set("X-Expected-Version", options.expectedVersion);
  const { signal, cleanup } = combineSignals(options.timeoutMs ?? 20_000, options.signal);
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers, signal, cache: "no-store" });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    const aborted = error instanceof DOMException && error.name === "AbortError";
    throw new StudioApiError(
      0,
      aborted
        ? "The local Studio did not respond in time. Check that the backend is running."
        : "The local Studio is unreachable. Check that the backend is running.",
      aborted ? "timeout" : "network_error",
    );
  } finally {
    cleanup();
  }
  if (!response.ok) {
    const raw = await response.text();
    let detail = raw;
    let code = response.headers?.get?.("X-Studio-Error-Code") || "request_failed";
    try {
      const parsed = JSON.parse(raw) as StudioErrorBody;
      if (typeof parsed.detail === "string") detail = parsed.detail;
      else if (Array.isArray(parsed.detail)) detail = parsed.detail.map((item) => item.msg || "").join("; ");
      else if (parsed.detail && typeof parsed.detail === "object") {
        detail = parsed.detail.detail || detail;
        code = parsed.detail.code || code;
      }
      if (typeof parsed.code === "string") code = parsed.code;
    } catch {
      /* non-JSON error body is already the detail */
    }
    throw new StudioApiError(response.status, detail || `Request failed (${response.status})`, code);
  }
  return (await response.json()) as T;
}

export function getStudioHealth(): Promise<StudioHealth> {
  return request("/animus/studio/health");
}

export function getStudioCapabilities(): Promise<StudioCapabilitiesResponse> {
  return request("/animus/studio/capabilities");
}

export function getStudioProfile(): Promise<StudioProfile> {
  return request<StudioProfile>("/animus/studio/profile");
}

export function resetStudioProfile(): Promise<StudioProfile> {
  return request<StudioProfile>("/animus/studio/profile/reset", { method: "POST" });
}

export function listStudioProtocols(): Promise<StudioProtocolList> {
  return request<StudioProtocolList>("/animus/studio/protocols");
}

export function startStudioPractice(
  sessionId: string,
  options: { taskType?: string; difficulty?: number } = {},
): Promise<PracticeStart> {
  return request<PracticeStart>(`/animus/studio/sessions/${sessionId}/practice/start`, {
    method: "POST",
    body: JSON.stringify({
      ...(options.taskType ? { task_type: options.taskType } : {}),
      ...(typeof options.difficulty === "number" ? { difficulty: options.difficulty } : {}),
    }),
  });
}

export function submitStudioPractice(
  sessionId: string,
  input: {
    taskType: string;
    taskId: string;
    taskSeed: number;
    difficulty: number;
    response?: PracticeResponse;
    optionId?: string;
    confidence: number;
    latencyMs: number;
    clientTrialId: string;
    expectedVersionId?: string;
  },
  options?: StudioRequestOptions,
): Promise<PracticeSubmit> {
  return request<PracticeSubmit>(
    `/animus/studio/sessions/${sessionId}/practice/trials`,
    {
      method: "POST",
      body: JSON.stringify({
        task_id: input.taskId,
        task_type: input.taskType,
        task_seed: input.taskSeed,
        difficulty: input.difficulty,
        response: input.response ?? { option_id: input.optionId ?? "" },
        confidence: input.confidence,
        latency_ms: input.latencyMs,
        client_trial_id: input.clientTrialId,
        ...(input.expectedVersionId ? { expected_version_id: input.expectedVersionId } : {}),
      }),
    },
    options,
  );
}

export function startStudioInterview(
  sessionId: string,
  options: {
    maxProbes?: number;
    formId?: "A" | "B" | "C";
    difficulty?: number;
    expectedVersionId?: string;
  } = {},
): Promise<InterviewStart> {
  return request<InterviewStart>(`/animus/studio/sessions/${sessionId}/interviews/start`, {
    method: "POST",
    body: JSON.stringify({
      ...(typeof options.maxProbes === "number" ? { max_probes: options.maxProbes } : {}),
      ...(options.formId ? { form_id: options.formId } : {}),
      ...(typeof options.difficulty === "number" ? { difficulty: options.difficulty } : {}),
      ...(options.expectedVersionId ? { expected_version_id: options.expectedVersionId } : {}),
    }),
  });
}

export function submitStudioInterview(
  sessionId: string,
  interviewId: string,
  input: {
    probeId: string;
    taskId: string;
    choice?: string;
    confidence: number;
    abstained?: boolean;
    latencyMs: number;
    clientTrialId: string;
    expectedVersionId?: string;
  },
  options?: StudioRequestOptions,
): Promise<InterviewSubmit> {
  return request<InterviewSubmit>(
    `/animus/studio/sessions/${sessionId}/interviews/${interviewId}/probes`,
    {
      method: "POST",
      body: JSON.stringify({
        probe_id: input.probeId,
        task_id: input.taskId,
        choice: input.choice ?? "",
        confidence: input.confidence,
        abstained: input.abstained ?? false,
        latency_ms: input.latencyMs,
        client_trial_id: input.clientTrialId,
        ...(input.expectedVersionId ? { expected_version_id: input.expectedVersionId } : {}),
      }),
    },
    options,
  );
}

export function getStudioInterview(interviewId: string): Promise<InterviewSummary> {
  return request<InterviewSummary>(`/animus/studio/interviews/${interviewId}`);
}

export function listStudioInterviews(sessionId: string): Promise<InterviewList> {
  return request<InterviewList>(`/animus/studio/sessions/${sessionId}/interviews`);
}

export function startStudioContrast(
  sessionId: string,
  options: {
    maxTrials?: number;
    formId?: "A" | "B" | "C";
    difficulty?: number;
    occasion?: "baseline" | "follow_up";
    delayHours?: number;
    sourceVersionId?: string;
    expectedVersionId?: string;
  } = {},
): Promise<ContrastStart> {
  return request<ContrastStart>(`/animus/studio/sessions/${sessionId}/contrast/start`, {
    method: "POST",
    body: JSON.stringify({
      ...(typeof options.maxTrials === "number" ? { max_trials: options.maxTrials } : {}),
      ...(options.formId ? { form_id: options.formId } : {}),
      ...(typeof options.difficulty === "number" ? { difficulty: options.difficulty } : {}),
      ...(options.occasion ? { occasion: options.occasion } : {}),
      ...(typeof options.delayHours === "number" ? { delay_hours: options.delayHours } : {}),
      ...(options.sourceVersionId ? { source_version_id: options.sourceVersionId } : {}),
      ...(options.expectedVersionId ? { expected_version_id: options.expectedVersionId } : {}),
    }),
  });
}

export function submitStudioContrast(
  sessionId: string,
  contrastId: string,
  input: {
    trialId: string;
    taskId: string;
    choice?: "a" | "b";
    confidence: number;
    abstained?: boolean;
    latencyMs: number;
    clientTrialId: string;
    expectedVersionId?: string;
  },
  options?: StudioRequestOptions,
): Promise<ContrastSubmit> {
  return request<ContrastSubmit>(
    `/animus/studio/sessions/${sessionId}/contrast/${contrastId}/trials`,
    {
      method: "POST",
      body: JSON.stringify({
        trial_id: input.trialId,
        task_id: input.taskId,
        choice: input.abstained ? "" : input.choice ?? "",
        confidence: input.confidence,
        abstained: input.abstained ?? false,
        latency_ms: input.latencyMs,
        client_trial_id: input.clientTrialId,
        ...(input.expectedVersionId ? { expected_version_id: input.expectedVersionId } : {}),
      }),
    },
    options,
  );
}

export function getStudioContrast(contrastId: string): Promise<ContrastSummary> {
  return request<ContrastSummary>(`/animus/studio/contrast/${contrastId}`);
}

export function listStudioContrasts(sessionId: string): Promise<ContrastList> {
  return request<ContrastList>(`/animus/studio/sessions/${sessionId}/contrast`);
}

export function getStudioObservatory(sessionId: string): Promise<Observatory> {
  return request<Observatory>(`/animus/studio/sessions/${sessionId}/observatory`);
}

export function submitStudioContrastReflection(
  contrastId: string,
  input: { strategies: string[]; notes?: string },
): Promise<ContrastSummary> {
  return request<ContrastSummary>(`/animus/studio/contrast/${contrastId}/reflection`, {
    method: "POST",
    body: JSON.stringify({ strategies: input.strategies, notes: input.notes ?? "" }),
  });
}

export function createStudioSession(input: StudioCreateInput): Promise<StudioSnapshot> {
  return request("/animus/studio/sessions", {
    method: "POST",
    body: JSON.stringify({ title: input.title, intention: input.intention, seed: input.seed ?? 20260909 }),
  });
}

export function listStudioSessions(limit = 30): Promise<StudioSessionList> {
  return request(`/animus/studio/sessions?limit=${limit}`);
}

export function getStudioSession(
  sessionId: string,
  options?: StudioRequestOptions,
): Promise<StudioSnapshot> {
  return request(`/animus/studio/sessions/${sessionId}`, undefined, options);
}

export function deleteStudioSession(sessionId: string): Promise<StudioDeleteResult> {
  return request(`/animus/studio/sessions/${sessionId}`, { method: "DELETE" });
}

export function applyStudioIntent(
  sessionId: string,
  text: string,
  options?: StudioRequestOptions,
): Promise<StudioIntentSnapshot> {
  return request(
    `/animus/studio/sessions/${sessionId}/intent`,
    { method: "POST", body: JSON.stringify({ text }) },
    options,
  );
}

export type SceneCommand = StudioSceneCommand;

export function applyStudioCommands(
  sessionId: string,
  commands: SceneCommand[],
  sourceText = "manual edit",
  options?: StudioRequestOptions,
): Promise<StudioCommandsSnapshot> {
  return request(
    `/animus/studio/sessions/${sessionId}/commands`,
    { method: "POST", body: JSON.stringify({ commands, source_text: sourceText }) },
    options,
  );
}

export function regenerateStudio(
  sessionId: string,
  options: StudioRegenerateOptions = {},
  requestOptions?: StudioRequestOptions,
): Promise<StudioRegenerateSnapshot> {
  return request(
    `/animus/studio/sessions/${sessionId}/regenerate`,
    {
      method: "POST",
      body: JSON.stringify({
        count: options.count ?? 3,
        strength: options.strength ?? 0.22,
        seed: options.seed,
        locks: options.locks ?? [],
        preserve_user_edits: options.preserveUserEdits ?? true,
        vary_camera: options.varyCamera ?? true,
      }),
    },
    requestOptions,
  );
}

export function selectStudioCandidate(
  sessionId: string,
  candidateId: string,
  options?: StudioRequestOptions,
): Promise<StudioSnapshot> {
  return request(
    `/animus/studio/sessions/${sessionId}/candidates/${candidateId}/select`,
    { method: "POST" },
    options,
  );
}

export function undoStudio(sessionId: string, options?: StudioRequestOptions): Promise<StudioSnapshot> {
  return request(`/animus/studio/sessions/${sessionId}/undo`, { method: "POST" }, options);
}

export function redoStudio(sessionId: string, options?: StudioRequestOptions): Promise<StudioSnapshot> {
  return request(`/animus/studio/sessions/${sessionId}/redo`, { method: "POST" }, options);
}

export function createStudioBranch(
  sessionId: string,
  input: StudioBranchInput = {},
  options?: StudioRequestOptions,
): Promise<StudioSnapshot> {
  return request(
    `/animus/studio/sessions/${sessionId}/branches`,
    { method: "POST", body: JSON.stringify(input) },
    options,
  );
}

export function switchStudioBranch(
  sessionId: string,
  branchId: string,
  options?: StudioRequestOptions,
): Promise<StudioSnapshot> {
  return request(
    `/animus/studio/sessions/${sessionId}/branches/${branchId}/switch`,
    { method: "POST" },
    options,
  );
}

export function getStudioHistory(sessionId: string): Promise<StudioHistory> {
  return request(`/animus/studio/sessions/${sessionId}/history`);
}

export function getStudioEvents(
  sessionId: string,
  afterSeq = 0,
  limit = 100,
): Promise<StudioEventsResponse> {
  return request(`/animus/studio/sessions/${sessionId}/events?after_seq=${afterSeq}&limit=${limit}`);
}

export function getStudioVersion(
  sessionId: string,
  versionId: string,
  options?: StudioRequestOptions,
): Promise<StudioVersionDetail> {
  return request(`/animus/studio/sessions/${sessionId}/versions/${versionId}`, undefined, options);
}

export function saveStudioWorld(
  sessionId: string,
  input: StudioWorldInput,
  options?: StudioRequestOptions,
): Promise<StudioWorldSaveResult> {
  return request(`/animus/studio/sessions/${sessionId}/worlds`, {
    method: "POST",
    body: JSON.stringify(input),
  }, options);
}

export function listStudioWorlds(limit = 40): Promise<StudioWorldList> {
  return request(`/animus/studio/worlds?limit=${limit}`);
}

export function getStudioWorld(worldId: string): Promise<StudioWorld> {
  return request(`/animus/studio/worlds/${worldId}`);
}

export function deleteStudioWorld(worldId: string): Promise<StudioDeleteResult> {
  return request(`/animus/studio/worlds/${worldId}`, { method: "DELETE" });
}

export function openStudioWorld(worldId: string, title?: string): Promise<StudioSnapshot> {
  return request(`/animus/studio/worlds/${worldId}/open`, {
    method: "POST",
    body: JSON.stringify(title ? { title } : {}),
  });
}

export function studioWebSocketUrl(sessionId: string): string {
  const encoded = encodeURIComponent(sessionId);
  const explicit = process.env.NEXT_PUBLIC_WS_URL;
  if (explicit) return `${explicit.replace(/\/$/, "")}/ws/animus/${encoded}`;
  return `${API_URL.replace(/^http/, "ws").replace(/\/$/, "")}/ws/animus/${encoded}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Validate the transport envelope before it reaches React state.
 *
 * This is deliberately shallow: the REST contract is enforced by Pydantic on the backend, while the
 * WebSocket is raw JSON and is the one boundary where a malformed frame must be ignored safely.
 */
export function parseStudioWebSocketMessage(raw: unknown): StudioWebSocketMessage | null {
  if (!isRecord(raw) || typeof raw.type !== "string") return null;
  switch (raw.type) {
    case "snapshot": {
      if (!isRecord(raw.session) || typeof raw.session.session_id !== "string") return null;
      return raw as unknown as StudioWebSocketMessage;
    }
    case "event": {
      if (typeof raw.event_type !== "string") return null;
      return raw as unknown as StudioWebSocketMessage;
    }
    case "resync_required":
      return {
        type: "resync_required",
        reason: typeof raw.reason === "string" ? raw.reason : undefined,
      };
    case "pong":
      return { type: "pong" };
    case "error": {
      if (typeof raw.code !== "string") return null;
      return {
        type: "error",
        code: raw.code,
        message: typeof raw.message === "string" ? raw.message : undefined,
      };
    }
    default:
      return null;
  }
}
