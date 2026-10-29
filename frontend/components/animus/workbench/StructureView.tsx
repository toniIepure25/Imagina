"use client";

import { useId, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { SceneEntity, SceneGraph, SceneRelation } from "@/lib/animusStudioApi";
import { SCENE_RELATIONS, relationLabel, type SceneRelationName } from "@/lib/sceneContract";
import { entityColor, entityKindLabel, isEntityLocked } from "../sceneUtils";

const WIDTH = 720;
const HEIGHT = 380;
const PAD = 46;

interface Placed {
  entity: SceneEntity;
  x: number;
  y: number;
}

function project(scene: SceneGraph, draft: Record<string, [number, number]>): {
  placed: Placed[];
  bounds: { minX: number; minZ: number; spanX: number; spanZ: number };
} {
  const entities = scene.entities;
  if (!entities.length) {
    return { placed: [], bounds: { minX: 0, minZ: 0, spanX: 1, spanZ: 1 } };
  }
  const positions = entities.map((entity) => draft[entity.id] ?? [entity.transform.position[0], entity.transform.position[2]]);
  const baseX = entities.map((entity) => entity.transform.position[0]);
  const baseZ = entities.map((entity) => entity.transform.position[2]);
  const minX = Math.min(...baseX);
  const maxX = Math.max(...baseX);
  const minZ = Math.min(...baseZ);
  const maxZ = Math.max(...baseZ);
  const spanX = Math.max(0.8, maxX - minX);
  const spanZ = Math.max(0.8, maxZ - minZ);
  return {
    placed: entities.map((entity, index) => ({
      entity,
      x: PAD + ((positions[index][0] - minX) / spanX) * (WIDTH - PAD * 2),
      y: PAD + ((positions[index][1] - minZ) / spanZ) * (HEIGHT - PAD * 2),
    })),
    bounds: { minX, minZ, spanX, spanZ },
  };
}

export default function StructureView({
  scene,
  selectedId,
  onSelect,
  onMove,
  onAddRelation,
  onRemoveRelation,
  readOnly,
  busy,
}: {
  scene: SceneGraph;
  selectedId: string | null;
  onSelect: (entityId: string | null) => void;
  onMove: (entityId: string, x: number, z: number) => Promise<boolean>;
  onAddRelation: (subjectId: string, relation: SceneRelationName, objectId: string) => Promise<boolean>;
  onRemoveRelation: (relation: SceneRelation) => Promise<boolean>;
  readOnly: boolean;
  busy: boolean;
}) {
  const markerId = useId().replace(/:/g, "");
  const svgRef = useRef<SVGSVGElement>(null);
  const [draft, setDraft] = useState<Record<string, [number, number]>>({});
  const dragRef = useRef<{ id: string; dx: number; dy: number } | null>(null);
  const [movingId, setMovingId] = useState<string | null>(null);
  const [subjectId, setSubjectId] = useState(scene.entities[0]?.id ?? "");
  const [objectId, setObjectId] = useState(scene.entities[1]?.id ?? scene.entities[0]?.id ?? "");
  const [relation, setRelation] = useState<SceneRelationName>("next_to");
  const [formError, setFormError] = useState<string | null>(null);

  const { placed, bounds } = useMemo(() => project(scene, draft), [draft, scene]);
  const byId = useMemo(() => new Map(placed.map((item) => [item.entity.id, item])), [placed]);

  const toLocal = (event: ReactPointerEvent<SVGElement>): { x: number; y: number } | null => {
    const svg = svgRef.current;
    if (!svg) return null;
    const matrix = svg.getScreenCTM();
    if (!matrix) return null;
    const point = svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const local = point.matrixTransform(matrix.inverse());
    return { x: local.x, y: local.y };
  };

  const toWorld = (local: { x: number; y: number }): [number, number] => {
    const x = bounds.minX + ((local.x - PAD) / (WIDTH - PAD * 2)) * bounds.spanX;
    const z = bounds.minZ + ((local.y - PAD) / (HEIGHT - PAD * 2)) * bounds.spanZ;
    return [Math.round(x * 100) / 100, Math.round(z * 100) / 100];
  };

  const beginDrag = (event: ReactPointerEvent<SVGGElement>, item: Placed) => {
    if (readOnly || busy || isEntityLocked(item.entity)) return;
    const local = toLocal(event);
    if (!local) return;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    dragRef.current = { id: item.entity.id, dx: item.x - local.x, dy: item.y - local.y };
    setMovingId(item.entity.id);
    onSelect(item.entity.id);
  };

  const moveDrag = (event: ReactPointerEvent<SVGGElement>) => {
    const drag = dragRef.current;
    if (!drag) return;
    const local = toLocal(event);
    if (!local) return;
    const x = Math.max(PAD, Math.min(WIDTH - PAD, local.x + drag.dx));
    const y = Math.max(PAD, Math.min(HEIGHT - PAD, local.y + drag.dy));
    const world = toWorld({ x, y });
    setDraft((current) => ({ ...current, [drag.id]: world }));
  };

  const endDrag = async (event: ReactPointerEvent<SVGGElement>) => {
    const drag = dragRef.current;
    dragRef.current = null;
    setMovingId(null);
    if (!drag) return;
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    const local = toLocal(event);
    if (!local) return;
    const x = Math.max(PAD, Math.min(WIDTH - PAD, local.x + drag.dx));
    const y = Math.max(PAD, Math.min(HEIGHT - PAD, local.y + drag.dy));
    const next = toWorld({ x, y });
    await onMove(drag.id, next[0], next[1]);
    setDraft((current) => {
      const copy = { ...current };
      delete copy[drag.id];
      return copy;
    });
  };

  const nudge = async (item: Placed, dx: number, dz: number) => {
    if (readOnly || busy || isEntityLocked(item.entity)) return;
    await onMove(
      item.entity.id,
      Math.round((item.entity.transform.position[0] + dx) * 100) / 100,
      Math.round((item.entity.transform.position[2] + dz) * 100) / 100,
    );
  };

  const addRelation = async () => {
    setFormError(null);
    if (!subjectId || !objectId) {
      setFormError("Choose both a subject and an object.");
      return;
    }
    if (subjectId === objectId) {
      setFormError("A relation needs two different elements.");
      return;
    }
    const applied = await onAddRelation(subjectId, relation, objectId);
    if (!applied) setFormError("The relation was not accepted. The scene is unchanged.");
  };

  return (
    <div className="grid gap-3 p-3 xl:grid-cols-[minmax(0,1fr)_310px]">
      <div className="instrument-panel relative min-h-[360px] overflow-hidden rounded-lg">
        <div className="pointer-events-none absolute left-3 top-3 z-10">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-signal/60">Top-down structure</p>
          <p className="mt-1 text-[11px] text-foreground/35">
            Drag an unlocked node to move it on the ground plane. Arrow keys nudge it.
          </p>
        </div>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="h-full min-h-[360px] w-full touch-none"
          role="group"
          aria-label="Scene structure graph"
        >
          <defs>
            <marker id={markerId} markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
              <path d="M 0 0 L 7 3.5 L 0 7 z" fill="rgba(236,231,218,0.55)" />
            </marker>
            <pattern id={`${markerId}-grid`} width="36" height="36" patternUnits="userSpaceOnUse">
              <path d="M 36 0 L 0 0 0 36" fill="none" stroke="rgba(236,231,218,0.055)" strokeWidth="0.7" />
            </pattern>
          </defs>
          <rect width={WIDTH} height={HEIGHT} fill="#080a0c" />
          <rect width={WIDTH} height={HEIGHT} fill={`url(#${markerId}-grid)`} />
          {scene.relations.map((relationItem, index) => {
            const from = byId.get(relationItem.subject_id);
            const to = byId.get(relationItem.object_id);
            if (!from || !to) return null;
            const mx = (from.x + to.x) / 2;
            const my = (from.y + to.y) / 2;
            return (
              <g key={`${relationItem.subject_id}-${relationItem.relation}-${relationItem.object_id}-${index}`}>
                <line
                  x1={from.x}
                  y1={from.y}
                  x2={to.x}
                  y2={to.y}
                  stroke="rgba(236,231,218,0.32)"
                  strokeWidth="1.1"
                  markerEnd={`url(#${markerId})`}
                />
                <text x={mx} y={my - 4} textAnchor="middle" fill="rgba(236,231,218,0.5)" fontSize="11" fontFamily="ui-monospace, monospace">
                  {relationLabel(relationItem.relation)}
                </text>
              </g>
            );
          })}
          {placed.map((item) => {
            const selected = selectedId === item.entity.id;
            const locked = isEntityLocked(item.entity);
            return (
              <g
                key={item.entity.id}
                role="button"
                tabIndex={0}
                aria-label={`${item.entity.label}, ${entityKindLabel(item.entity.kind)}${locked ? ", locked" : ""}`}
                aria-pressed={selected}
                data-testid={`structure-node-${item.entity.id}`}
                style={{ cursor: readOnly || locked ? "default" : "grab" }}
                onPointerDown={(event) => beginDrag(event, item)}
                onPointerMove={moveDrag}
                onPointerUp={(event) => void endDrag(event)}
                onPointerCancel={() => {
                  dragRef.current = null;
                  setMovingId(null);
                }}
                onClick={() => onSelect(item.entity.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect(item.entity.id);
                  } else if (event.key === "ArrowLeft") {
                    event.preventDefault();
                    void nudge(item, -0.2, 0);
                  } else if (event.key === "ArrowRight") {
                    event.preventDefault();
                    void nudge(item, 0.2, 0);
                  } else if (event.key === "ArrowUp") {
                    event.preventDefault();
                    void nudge(item, 0, -0.2);
                  } else if (event.key === "ArrowDown") {
                    event.preventDefault();
                    void nudge(item, 0, 0.2);
                  }
                }}
              >
                <circle cx={item.x} cy={item.y} r={selected ? 22 : 18} fill="transparent" />
                <circle
                  cx={item.x}
                  cy={item.y}
                  r={selected ? 15 : 13}
                  fill={entityColor(item.entity)}
                  opacity={movingId === item.entity.id ? 0.65 : 0.9}
                  stroke={selected ? "#6fe3c4" : locked ? "#e8b45a" : "rgba(0,0,0,0.45)"}
                  strokeWidth={selected || locked ? 2.4 : 1}
                />
                <text x={item.x} y={item.y + 3.2} textAnchor="middle" fontSize="11" fill="#07080a" fontWeight="700">
                  {item.entity.label.slice(0, 2).toUpperCase()}
                </text>
                <text x={item.x} y={item.y + 30} textAnchor="middle" fontSize="11" fill="rgba(236,231,218,0.72)">
                  {item.entity.label.length > 22 ? `${item.entity.label.slice(0, 21)}…` : item.entity.label}
                </text>
                {locked ? (
                  <text x={item.x + 12} y={item.y - 12} fontSize="11" fill="#e8b45a" aria-hidden="true">
                    ⌑
                  </text>
                ) : null}
              </g>
            );
          })}
          {placed.length === 0 ? (
            <text x={WIDTH / 2} y={HEIGHT / 2} textAnchor="middle" fill="rgba(236,231,218,0.4)" fontSize="11">
              No elements yet. Add one from the inspector.
            </text>
          ) : null}
        </svg>
      </div>

      <aside className="space-y-3">
        <section className="instrument-panel rounded-lg p-3">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.2em] text-foreground/35">Add relation</h2>
          <div className="mt-2 space-y-2">
            <label className="block text-[11px] text-foreground/45">
              Subject
              <select
                value={subjectId}
                onChange={(event) => setSubjectId(event.target.value)}
                disabled={readOnly || busy || !scene.entities.length}
                className="mt-1 w-full rounded border border-white/10 bg-[#0b0d10] px-2 py-1.5 text-[11px] text-foreground/75 disabled:opacity-40"
              >
                {scene.entities.map((entity) => (
                  <option key={entity.id} value={entity.id}>{entity.label}</option>
                ))}
              </select>
            </label>
            <label className="block text-[11px] text-foreground/45">
              Relation
              <select
                value={relation}
                onChange={(event) => setRelation(event.target.value as SceneRelationName)}
                disabled={readOnly || busy || !scene.entities.length}
                className="mt-1 w-full rounded border border-white/10 bg-[#0b0d10] px-2 py-1.5 text-[11px] text-foreground/75 disabled:opacity-40"
              >
                {SCENE_RELATIONS.map((item) => (
                  <option key={item} value={item}>{relationLabel(item)}</option>
                ))}
              </select>
            </label>
            <label className="block text-[11px] text-foreground/45">
              Object
              <select
                value={objectId}
                onChange={(event) => setObjectId(event.target.value)}
                disabled={readOnly || busy || !scene.entities.length}
                className="mt-1 w-full rounded border border-white/10 bg-[#0b0d10] px-2 py-1.5 text-[11px] text-foreground/75 disabled:opacity-40"
              >
                {scene.entities.map((entity) => (
                  <option key={entity.id} value={entity.id}>{entity.label}</option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={() => void addRelation()}
              disabled={readOnly || busy || scene.entities.length < 2}
              className="w-full rounded border border-signal/30 bg-signal/10 px-2 py-1.5 text-[11px] text-signal disabled:opacity-35"
            >
              Add relation
            </button>
            {formError ? <p role="alert" className="text-[11px] text-red-300/80">{formError}</p> : null}
          </div>
        </section>

        <section className="instrument-panel rounded-lg p-3">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.2em] text-foreground/35">
            Relations · {scene.relations.length}
          </h2>
          {scene.relations.length === 0 ? (
            <p className="mt-2 text-[11px] text-foreground/35">No relations yet. The scene is still valid.</p>
          ) : (
            <ul className="mt-2 max-h-52 space-y-1 overflow-y-auto pr-1">
              {scene.relations.map((item, index) => {
                const from = scene.entities.find((entity) => entity.id === item.subject_id);
                const to = scene.entities.find((entity) => entity.id === item.object_id);
                return (
                  <li key={`${item.subject_id}-${item.relation}-${item.object_id}-${index}`} className="flex items-start gap-2 rounded border border-white/8 px-2 py-1.5">
                    <span className="min-w-0 flex-1 text-[11px] leading-relaxed text-foreground/55">
                      <strong className="font-medium text-foreground/75">{from?.label ?? item.subject_id}</strong>{" "}
                      {relationLabel(item.relation)}{" "}
                      <strong className="font-medium text-foreground/75">{to?.label ?? item.object_id}</strong>
                    </span>
                    <button
                      type="button"
                      aria-label={`Remove relation ${relationLabel(item.relation)}`}
                      disabled={readOnly || busy}
                      onClick={() => void onRemoveRelation(item)}
                      className="shrink-0 rounded px-1 text-[11px] text-foreground/30 hover:text-red-300 disabled:opacity-30"
                    >
                      ×
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        {scene.constraints.length ? (
          <section className="instrument-panel rounded-lg p-3">
            <h2 className="font-mono text-[11px] uppercase tracking-[0.2em] text-foreground/35">Constraints</h2>
            <ul className="mt-2 space-y-1.5">
              {scene.constraints.map((constraint, index) => (
                <li key={`${constraint.kind}-${constraint.target}-${index}`} className="text-[11px] leading-relaxed text-foreground/45">
                  <span className="font-mono text-[11px] uppercase text-lock/70">{constraint.kind}</span>{" "}
                  {constraint.target} · {String(constraint.value)} · {constraint.provenance}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <details className="instrument-panel rounded-lg p-3">
          <summary className="cursor-pointer font-mono text-[11px] uppercase tracking-[0.2em] text-foreground/35">
            Table view
          </summary>
          <table className="mt-2 w-full text-left text-[11px] text-foreground/55">
            <caption className="sr-only">Scene elements and their positions</caption>
            <thead>
              <tr className="text-foreground/30">
                <th scope="col" className="py-1 font-normal">Element</th>
                <th scope="col" className="py-1 font-normal">x</th>
                <th scope="col" className="py-1 font-normal">z</th>
              </tr>
            </thead>
            <tbody>
              {scene.entities.map((entity) => (
                <tr key={entity.id} className="border-t border-white/6">
                  <td className="py-1.5">
                    <button type="button" onClick={() => onSelect(entity.id)} className="hover:text-signal">
                      {entity.label}
                    </button>
                  </td>
                  <td className="py-1.5 font-mono">{entity.transform.position[0].toFixed(2)}</td>
                  <td className="py-1.5 font-mono">{entity.transform.position[2].toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </aside>
    </div>
  );
}
