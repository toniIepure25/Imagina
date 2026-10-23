import { afterEach, describe, expect, it, vi } from "vitest";
import {
  StudioApiError,
  applyStudioIntent,
  createStudioSession,
  getStudioEvents,
  parseStudioWebSocketMessage,
  studioWebSocketUrl,
  type SceneEntity,
  type SceneGraph,
} from "@/lib/animusStudioApi";
import {
  attrColor,
  attrNumber,
  clamp,
  entityKindLabel,
  hexToRgba,
  isLocked,
  lockedAttributePaths,
  sceneGradient,
  scenePalette,
} from "@/components/animus/sceneUtils";

function entity(overrides: Partial<SceneEntity> = {}): SceneEntity {
  return {
    id: "ent_1",
    kind: "castle",
    label: "Castle",
    role: "subject",
    transform: { position: [0, 0, 0], rotation: [0, 0, 0], scale: [1, 1, 1] },
    attributes: {
      color: { value: "#e14b4b", confidence: 1, provenance: "USER_EXPLICIT", locked: false, renderable: true },
      size: { value: 1.2, confidence: 1, provenance: "USER_EXPLICIT", locked: false, renderable: true },
    },
    confidence: 1,
    provenance: "USER_EXPLICIT",
    locked: false,
    visible: true,
    parent_id: null,
    ...overrides,
  };
}

function scene(overrides: Partial<SceneGraph> = {}): SceneGraph {
  return {
    scene_id: "scene_test",
    version: 1,
    seed: 7,
    title: "Castle",
    version_tag: "ANIMUS-SG-v1",
    entities: [entity()],
    relations: [],
    style: "cinematic",
    camera: { position: [0, 2, 8], target: [0, 1, 0], fov: 55, motion: "static", speed: 0.2 },
    lighting: {
      key: { color: "#ffffff", intensity: 2, direction: [3, 5, 2] },
      ambient: { color: "#8899ff", intensity: 0.4 },
      rim: { color: "#79e8ff", intensity: 1 },
    },
    atmosphere: {
      fog: { color: "#0b1020", density: 0.01 },
      sky: { top: "#101a3a", horizon: "#d78a63", bottom: "#07080f", stars: 80, aurora: false },
      weather: "clear",
      time_of_day: "dusk",
    },
    dynamics: { wind: 0.1, water: 0.2, fire: 0, floating: 0.1, pulse: 0 },
    constraints: [],
    metadata: { content_hash: "abc123" },
    ...overrides,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("scene utilities", () => {
  it("maps provenance-safe defaults and rejects unsafe colour strings", () => {
    const castle = entity();
    expect(attrColor(castle, "color", "#000000")).toBe("#e14b4b");
    expect(attrColor(castle, "missing", "#123456")).toBe("#123456");
    expect(attrNumber(castle, "size", 1)).toBe(1.2);
    expect(attrNumber(castle, "missing", 1)).toBe(1);
  });

  it("detects element and attribute locks", () => {
    const lockedEntity = entity({ locked: true });
    expect(isLocked(lockedEntity)).toBe(true);
    const lockedColor = entity({
      attributes: {
        color: { value: "#fff", confidence: 1, provenance: "USER_EXPLICIT", locked: true, renderable: true },
      },
    });
    expect(lockedAttributePaths(lockedColor)).toEqual(["color"]);
    expect(isLocked(lockedColor)).toBe(true);
  });

  it("builds a subject-first palette and CSS gradient", () => {
    const subject = entity();
    const background = entity({ id: "ent_2", kind: "ocean", label: "Ocean", role: "background", attributes: {
      color: { value: "#14324a", confidence: 1, provenance: "USER_IMPLIED", locked: false, renderable: true },
    } });
    const graph = scene({ entities: [background, subject] });
    const palette = scenePalette(graph);
    expect(palette[0]).toBe("#101a3a");
    expect(palette).toContain("#e14b4b");
    expect(sceneGradient(graph)).toContain("linear-gradient");
  });

  it("formats kinds and utility values", () => {
    expect(entityKindLabel("floating_island")).toBe("Floating Island");
    expect(hexToRgba("#ff0000", 0.5)).toBe("rgba(255, 0, 0, 0.5)");
    expect(hexToRgba("nope", 0.5)).toBe("rgba(120, 140, 200, 0.5)");
    expect(clamp(2, 0, 1)).toBe(1);
  });
});

describe("studio API client", () => {
  it("posts a session and preserves the backend snapshot", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ session_id: "ast_1", scene: scene() }),
      text: async () => "",
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await createStudioSession({ title: "Castle", intention: "a castle", seed: 5 });
    expect(result.session_id).toBe("ast_1");
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/animus/studio/sessions");
    expect(init.cache).toBe("no-store");
    expect(JSON.parse(String(init.body))).toEqual({ title: "Castle", intention: "a castle", seed: 5 });
  });

  it("surfaces backend detail and status as a typed error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      headers: { get: () => null },
      text: async () => JSON.stringify({ detail: "mind-reading copy is not allowed" }),
    }));

    await expect(createStudioSession({ title: "x", intention: "a castle" })).rejects.toMatchObject({
      name: "StudioApiError",
      status: 400,
      detail: "mind-reading copy is not allowed",
      code: "request_failed",
    });
    await expect(createStudioSession({ title: "x", intention: "a castle" })).rejects.toBeInstanceOf(StudioApiError);
  });

  it("forwards optimistic-concurrency headers and exposes stable error codes", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      headers: { get: (name: string) => (name === "X-Studio-Error-Code" ? "stale_version" : null) },
      text: async () => JSON.stringify({ detail: "The scene changed" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      applyStudioIntent("ast_1", "make the sky violet", { expectedVersion: "ver_1" }),
    ).rejects.toMatchObject({ status: 409, code: "stale_version", retryable: true });
    const [, init] = fetchMock.mock.calls[0];
    expect((init.headers as Headers).get("X-Expected-Version")).toBe("ver_1");
  });

  it("derives the local websocket URL without extra configuration", () => {
    expect(studioWebSocketUrl("ast_123")).toMatch(/^wss?:\/\/.+\/ws\/animus\/ast_123$/);
    expect(studioWebSocketUrl("ast/with space")).toContain("ast%2Fwith%20space");
  });

  it("reports a timeout without masking the local backend message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("aborted", "AbortError")));

    await expect(createStudioSession({ title: "x", intention: "a castle" })).rejects.toMatchObject({
      status: 0,
      code: "timeout",
      retryable: true,
    });
  });

  it("reads the durable event history with an explicit cursor", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        session_id: "ast_1",
        events: [{
          seq: 4, session_id: "ast_1", event_type: "intention_applied", version_id: "ver_2",
          payload: {}, created_at: "2026-01-01T00:00:00Z",
        }],
        has_more: false,
      }),
      text: async () => "",
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await getStudioEvents("ast_1", 3, 10);
    expect(result.events[0].seq).toBe(4);
    const [url] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/animus/studio/sessions/ast_1/events?after_seq=3&limit=10");
  });

  it("accepts only well-formed websocket envelopes", () => {
    expect(parseStudioWebSocketMessage({ type: "pong" })).toEqual({ type: "pong" });
    expect(parseStudioWebSocketMessage({
      type: "snapshot", session: { session_id: "ast_1" },
    })).toEqual({ type: "snapshot", session: { session_id: "ast_1" } });
    expect(parseStudioWebSocketMessage({ type: "event", event_type: "intention_applied" })).toMatchObject({
      type: "event",
      event_type: "intention_applied",
    });
    expect(parseStudioWebSocketMessage({ type: "resync_required", reason: "queue_overflow" })).toEqual({
      type: "resync_required",
      reason: "queue_overflow",
    });
    expect(parseStudioWebSocketMessage({ type: "snapshot" })).toBeNull();
    expect(parseStudioWebSocketMessage({ type: "event" })).toBeNull();
    expect(parseStudioWebSocketMessage({ type: "error" })).toBeNull();
    expect(parseStudioWebSocketMessage("not json")).toBeNull();
    expect(parseStudioWebSocketMessage({ type: "future" })).toBeNull();
  });
});
