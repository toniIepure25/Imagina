import { describe, expect, it } from "vitest";
import type { SceneAttribute, SceneEntity, SceneGraph } from "@/lib/animusStudioApi";
import { compareScenes, comparisonSets, traceEntities } from "../sceneCompare";

function attribute(value: unknown, overrides: Partial<SceneAttribute> = {}): SceneAttribute {
  return {
    value,
    confidence: 0.8,
    provenance: "user_explicit",
    locked: false,
    renderable: true,
    source_text: null,
    ...overrides,
  };
}

function entity(id: string, overrides: Partial<SceneEntity> = {}): SceneEntity {
  return {
    id,
    kind: "sphere",
    label: id,
    role: "subject",
    transform: { position: [0, 0, 0], rotation: [0, 0, 0], scale: [1, 1, 1] },
    attributes: { color: attribute("#ffffff"), size: attribute(1) },
    confidence: 0.8,
    provenance: "user_explicit",
    locked: false,
    visible: true,
    parent_id: null,
    ...overrides,
  };
}

function scene(entities: SceneEntity[]): SceneGraph {
  return {
    scene_id: "scene",
    version: 1,
    seed: 1,
    title: "Test scene",
    version_tag: "test",
    entities,
    relations: [],
    style: "symbolic",
    camera: { position: [0, 4, 12], target: [0, 0, 0], fov: 45, motion: "still", speed: 0 },
    lighting: {
      key: { color: "#ffffff", intensity: 1, direction: [0, -1, 0] },
      ambient: { color: "#ffffff", intensity: 0.4 },
      rim: { color: "#ffffff", intensity: 0.2 },
    },
    atmosphere: {
      fog: { color: "#000000", density: 0.1 },
      sky: { top: "#000000", horizon: "#111111", bottom: "#222222", stars: 0, aurora: false },
      weather: "clear",
      time_of_day: "dusk",
    },
    dynamics: { wind: 0, water: 0, fire: 0, floating: 0, pulse: 0 },
    constraints: [],
    metadata: {},
  };
}

describe("compareScenes", () => {
  it("finds added, removed, and transformed entities", () => {
    const before = scene([
      entity("a", { transform: { position: [0, 0, 0], rotation: [0, 0, 0], scale: [1, 1, 1] } }),
      entity("b"),
      entity("gone"),
    ]);
    const after = scene([
      entity("a", {
        transform: { position: [2, 0, 0], rotation: [0, 0, 0], scale: [1, 1, 1] },
        label: "A moved",
      }),
      entity("b"),
      entity("new"),
    ]);

    const comparison = compareScenes(before, after);
    expect(comparison.added.map((item) => item.entity_id)).toEqual(["new"]);
    expect(comparison.removed.map((item) => item.entity_id)).toEqual(["gone"]);
    expect(comparison.changed.some((item) => item.path === "transform.position.x")).toBe(true);
    expect(comparison.changed.some((item) => item.path === "label")).toBe(true);
  });

  it("detects attribute provenance changes and keeps locked untouched entities", () => {
    const before = scene([
      entity("a", { locked: true, attributes: { color: attribute("#ffffff") } }),
      entity("b", { attributes: { color: attribute("#ffffff", { provenance: "candidate" }) } }),
    ]);
    const after = scene([
      entity("a", { locked: true, attributes: { color: attribute("#ffffff") } }),
      entity("b", { attributes: { color: attribute("#ffffff", { provenance: "user_implied" }) } }),
    ]);

    const comparison = compareScenes(before, after);
    expect(comparison.locked_untouched).toEqual(["a"]);
    expect(comparison.changed).toContainEqual(
      expect.objectContaining({
        entity_id: "b",
        path: "attributes.color.provenance",
        before: "candidate",
        after: "user_implied",
      }),
    );
  });

  it("does not report unchanged scenes", () => {
    const before = scene([entity("a")]);
    expect(compareScenes(before, structuredClone(before))).toEqual({
      added: [],
      removed: [],
      changed: [],
      locked_untouched: [],
    });
  });

  it("reports scene-level changes without inventing an entity", () => {
    const before = scene([entity("a")]);
    const after = structuredClone(before);
    after.atmosphere.sky.top = "#5522aa";

    const comparison = compareScenes(before, after);
    expect(comparison.changed).toContainEqual(
      expect.objectContaining({
        scope: "scene",
        entity_id: null,
        label: "Scene",
        path: "atmosphere.sky.top",
        before: "#000000",
        after: "#5522aa",
      }),
    );
    expect(comparisonSets(comparison).changed.size).toBe(0);
  });
});

describe("comparisonSets", () => {
  it("deduplicates changed entities across paths and keeps added and removed IDs", () => {
    const before = scene([
      entity("moved", { transform: { position: [0, 0, 0], rotation: [0, 0, 0], scale: [1, 1, 1] } }),
      entity("removed"),
    ]);
    const after = scene([
      entity("moved", {
        label: "Moved",
        transform: { position: [2, 0, 0], rotation: [0, 0, 0], scale: [1, 1, 1] },
      }),
      entity("added"),
    ]);

    const sets = comparisonSets(compareScenes(before, after));
    expect([...sets.added]).toEqual(["added"]);
    expect([...sets.removed]).toEqual(["removed"]);
    expect([...sets.changed]).toEqual(["moved"]);
  });

  it("returns empty sets for an unchanged comparison", () => {
    const before = scene([entity("a")]);
    const sets = comparisonSets(compareScenes(before, structuredClone(before)));
    expect(sets.added.size).toBe(0);
    expect(sets.changed.size).toBe(0);
    expect(sets.removed.size).toBe(0);
  });
});

describe("traceEntities", () => {
  it("returns moved and removed entities, then caps the result", () => {
    const before = scene([
      entity("moved", { transform: { position: [0, 0, 0], rotation: [0, 0, 0], scale: [1, 1, 1] } }),
      entity("removed"),
      entity("static"),
    ]);
    const after = scene([
      entity("moved", { transform: { position: [3, 0, 0], rotation: [0, 0, 0], scale: [1, 1, 1] } }),
      entity("static"),
    ]);
    const comparison = compareScenes(before, after);
    const traces = traceEntities(before, after, comparison, 1);
    expect(traces.total).toBe(2);
    expect(traces.shown).toBe(1);
    expect(traces.omitted).toBe(1);
    expect(traces.items[0]).toMatchObject({ state: "changed", nextPosition: [3, 0, 0] });
  });

  it("does not trace attribute-only changes", () => {
    const before = scene([entity("a", { attributes: { color: attribute("#ffffff") } })]);
    const after = scene([entity("a", { attributes: { color: attribute("#ff0000") } })]);
    const comparison = compareScenes(before, after);
    expect(traceEntities(before, after, comparison).items).toEqual([]);
    expect(comparison.changed.some((item) => item.path === "attributes.color")).toBe(true);
  });
});
