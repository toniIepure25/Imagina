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
): Promise<StudioVersionDetail> {
  return request(`/animus/studio/sessions/${sessionId}/versions/${versionId}`);
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
