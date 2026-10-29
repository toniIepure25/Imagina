import type { SceneAttribute, SceneDiff, SceneEntity, SceneGraph, Vec3 } from "@/lib/animusStudioApi";

export interface SceneComparison {
  added: SceneDiff["added"];
  removed: SceneDiff["removed"];
  changed: SceneDiff["changed"];
  locked_untouched: string[];
}

export interface TraceEntity {
  entity: SceneEntity;
  state: "changed" | "removed";
  nextPosition?: Vec3;
}

export interface TraceSet {
  items: TraceEntity[];
  total: number;
  shown: number;
  omitted: number;
}

export interface ComparisonSets {
  added: Set<string>;
  changed: Set<string>;
  removed: Set<string>;
}

const EPSILON = 1e-9;

function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.keys(value as Record<string, unknown>)
      .sort()
      .reduce<Record<string, unknown>>((result, key) => {
        result[key] = canonical((value as Record<string, unknown>)[key]);
        return result;
      }, {});
  }
  return value;
}

function stableKey(value: unknown): string {
  const serialized = JSON.stringify(canonical(value));
  return serialized === undefined ? String(value) : serialized;
}

function sameValue(left: unknown, right: unknown): boolean {
  return stableKey(left) === stableKey(right);
}

function sameNumber(left: number, right: number): boolean {
  return Math.abs(left - right) <= EPSILON;
}

function samePosition(left: Vec3, right: Vec3): boolean {
  return left.every((value, index) => sameNumber(value, right[index]));
}

function changedRow(
  entity: SceneEntity,
  scope: string,
  path: string,
  before: unknown,
  after: unknown,
  provenance: string,
): SceneDiff["changed"][number] {
  return {
    scope,
    entity_id: entity.id,
    label: entity.label,
    path,
    before,
    after,
    provenance,
  };
}

function entityRows(before: SceneEntity, after: SceneEntity): SceneDiff["changed"] {
  const rows: SceneDiff["changed"] = [];
  const scalarFields: Array<[string, unknown, unknown, string]> = [
    ["label", before.label, after.label, after.provenance],
    ["kind", before.kind, after.kind, after.provenance],
    ["role", before.role, after.role, after.provenance],
    ["locked", before.locked, after.locked, after.provenance],
    ["visible", before.visible, after.visible, after.provenance],
    ["parent_id", before.parent_id, after.parent_id, after.provenance],
    ["confidence", before.confidence, after.confidence, after.provenance],
    ["provenance", before.provenance, after.provenance, after.provenance],
  ];
  for (const [path, left, right, provenance] of scalarFields) {
    if (!sameValue(left, right)) rows.push(changedRow(after, "entity", path, left, right, provenance));
  }

  const axes = ["x", "y", "z"] as const;
  for (let index = 0; index < axes.length; index += 1) {
    const axis = axes[index];
    if (!sameNumber(before.transform.position[index], after.transform.position[index])) {
      rows.push(
        changedRow(
          after,
          "transform",
          `transform.position.${axis}`,
          before.transform.position[index],
          after.transform.position[index],
          after.provenance,
        ),
      );
    }
    if (!sameNumber(before.transform.rotation[index], after.transform.rotation[index])) {
      rows.push(
        changedRow(
          after,
          "transform",
          `transform.rotation.${axis}`,
          before.transform.rotation[index],
          after.transform.rotation[index],
          after.provenance,
        ),
      );
    }
    if (!sameNumber(before.transform.scale[index], after.transform.scale[index])) {
      rows.push(
        changedRow(
          after,
          "transform",
          `transform.scale.${axis}`,
          before.transform.scale[index],
          after.transform.scale[index],
          after.provenance,
        ),
      );
    }
  }

  const attributePaths = new Set([...Object.keys(before.attributes), ...Object.keys(after.attributes)]);
  for (const path of [...attributePaths].sort()) {
    const left = before.attributes[path];
    const right = after.attributes[path];
    if (!left || !right) {
      rows.push(
        changedRow(
          after,
          "attribute",
          `attributes.${path}`,
          left ? attributeValue(left) : undefined,
          right ? attributeValue(right) : undefined,
          right?.provenance ?? left?.provenance ?? after.provenance,
        ),
      );
      continue;
    }
    const fields: Array<[string, unknown, unknown, string]> = [
      ["value", left.value, right.value, right.provenance],
      ["confidence", left.confidence, right.confidence, right.provenance],
      ["provenance", left.provenance, right.provenance, right.provenance],
      ["locked", left.locked, right.locked, right.provenance],
      ["renderable", left.renderable, right.renderable, right.provenance],
      ["source_text", left.source_text, right.source_text, right.provenance],
    ];
    for (const [field, beforeValue, afterValue, provenance] of fields) {
      if (!sameValue(beforeValue, afterValue)) {
        const suffix = field === "value" ? "" : `.${field}`;
        rows.push(
          changedRow(after, "attribute", `attributes.${path}${suffix}`, beforeValue, afterValue, provenance),
        );
      }
    }
  }
  return rows;
}

function attributeValue(attribute: SceneAttribute): unknown {
  return attribute.value;
}

function sceneRows(before: SceneGraph, after: SceneGraph): SceneDiff["changed"] {
  const pairs: Array<[string, unknown, unknown]> = [
    ["title", before.title, after.title],
    ["style", before.style, after.style],
    ["atmosphere.time_of_day", before.atmosphere.time_of_day, after.atmosphere.time_of_day],
    ["atmosphere.weather", before.atmosphere.weather, after.atmosphere.weather],
    ["atmosphere.fog.color", before.atmosphere.fog.color, after.atmosphere.fog.color],
    ["atmosphere.fog.density", before.atmosphere.fog.density, after.atmosphere.fog.density],
    ["atmosphere.sky.top", before.atmosphere.sky.top, after.atmosphere.sky.top],
    ["atmosphere.sky.horizon", before.atmosphere.sky.horizon, after.atmosphere.sky.horizon],
    ["atmosphere.sky.bottom", before.atmosphere.sky.bottom, after.atmosphere.sky.bottom],
    ["atmosphere.sky.stars", before.atmosphere.sky.stars, after.atmosphere.sky.stars],
    ["atmosphere.sky.aurora", before.atmosphere.sky.aurora, after.atmosphere.sky.aurora],
    ["lighting.key.color", before.lighting.key.color, after.lighting.key.color],
    ["lighting.key.intensity", before.lighting.key.intensity, after.lighting.key.intensity],
    ["lighting.key.direction", before.lighting.key.direction, after.lighting.key.direction],
    ["lighting.ambient.color", before.lighting.ambient.color, after.lighting.ambient.color],
    ["lighting.ambient.intensity", before.lighting.ambient.intensity, after.lighting.ambient.intensity],
    ["lighting.rim.color", before.lighting.rim.color, after.lighting.rim.color],
    ["lighting.rim.intensity", before.lighting.rim.intensity, after.lighting.rim.intensity],
    ["camera.position", before.camera.position, after.camera.position],
    ["camera.target", before.camera.target, after.camera.target],
    ["camera.fov", before.camera.fov, after.camera.fov],
    ["camera.motion", before.camera.motion, after.camera.motion],
    ["camera.speed", before.camera.speed, after.camera.speed],
    ["dynamics.wind", before.dynamics.wind, after.dynamics.wind],
    ["dynamics.water", before.dynamics.water, after.dynamics.water],
    ["dynamics.fire", before.dynamics.fire, after.dynamics.fire],
    ["dynamics.floating", before.dynamics.floating, after.dynamics.floating],
    ["dynamics.pulse", before.dynamics.pulse, after.dynamics.pulse],
  ];
  return pairs
    .filter(([, beforeValue, afterValue]) => !sameValue(beforeValue, afterValue))
    .map(([path, beforeValue, afterValue]) => ({
      scope: "scene",
      entity_id: null,
      label: "Scene",
      path,
      before: beforeValue,
      after: afterValue,
      provenance: "scene",
    }));
}

export function compareScenes(before: SceneGraph, after: SceneGraph): SceneComparison {
  const beforeById = new Map(before.entities.map((entity) => [entity.id, entity]));
  const afterById = new Map(after.entities.map((entity) => [entity.id, entity]));
  const added: SceneDiff["added"] = [];
  const removed: SceneDiff["removed"] = [];
  const changed: SceneDiff["changed"] = [];
  const lockedUntouched: string[] = [];

  for (const entity of before.entities) {
    const next = afterById.get(entity.id);
    if (!next) {
      removed.push({ entity_id: entity.id, label: entity.label, kind: entity.kind });
      continue;
    }
    const rows = entityRows(entity, next);
    if (rows.length) changed.push(...rows);
    else if (entity.locked) lockedUntouched.push(entity.label);
  }

  for (const entity of after.entities) {
    if (!beforeById.has(entity.id)) {
      added.push({ entity_id: entity.id, label: entity.label, kind: entity.kind });
    }
  }

  return { added, removed, changed: [...changed, ...sceneRows(before, after)], locked_untouched: lockedUntouched };
}

export function comparisonSets(comparison: SceneComparison): ComparisonSets {
  return {
    added: new Set(comparison.added.map((item) => item.entity_id)),
    changed: new Set(
      comparison.changed
        .map((item) => item.entity_id)
        .filter((entityId): entityId is string => Boolean(entityId)),
    ),
    removed: new Set(comparison.removed.map((item) => item.entity_id)),
  };
}

export function traceEntities(
  before: SceneGraph,
  after: SceneGraph,
  comparison: SceneComparison,
  cap = 16,
): TraceSet {
  const beforeById = new Map(before.entities.map((entity) => [entity.id, entity]));
  const afterById = new Map(after.entities.map((entity) => [entity.id, entity]));
  const changedIds = new Set(comparison.changed.map((item) => item.entity_id).filter(Boolean));
  const items: TraceEntity[] = [];

  for (const entity of before.entities) {
    if (!changedIds.has(entity.id)) continue;
    const next = afterById.get(entity.id);
    if (!next || samePosition(entity.transform.position, next.transform.position)) continue;
    items.push({ entity, state: "changed", nextPosition: next.transform.position });
  }

  for (const item of comparison.removed) {
    const entity = beforeById.get(item.entity_id);
    if (entity) items.push({ entity, state: "removed" });
  }

  const safeCap = Math.max(0, Math.floor(cap));
  const limited = items.slice(0, safeCap);
  return {
    items: limited,
    total: items.length,
    shown: limited.length,
    omitted: Math.max(0, items.length - limited.length),
  };
}
