"use client";

import type { SceneGraph } from "@/lib/animusStudioApi";
import { entityColor, entityKindLabel } from "./sceneUtils";

function project(value: number, min: number, max: number): number {
  if (max - min < 0.001) return 50;
  return 10 + ((value - min) / (max - min)) * 80;
}

export default function SceneNavigator({
  scene,
  selectedId,
  onSelect,
}: {
  scene: SceneGraph;
  selectedId: string | null;
  onSelect: (entityId: string | null) => void;
}) {
  const entities = scene.entities.filter((entity) => entity.visible);
  if (entities.length === 0) return null;

  const xs = entities.map((entity) => entity.transform.position[0]);
  const zs = entities.map((entity) => entity.transform.position[2]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minZ = Math.min(...zs);
  const maxZ = Math.max(...zs);
  const selected = entities.find((entity) => entity.id === selectedId) ?? null;
  const points = new Map<string, { x: number; y: number }>(
    entities.map((entity): [string, { x: number; y: number }] => [
      entity.id,
      {
        x: project(entity.transform.position[0], minX, maxX),
        y: 100 - project(entity.transform.position[2], minZ, maxZ),
      },
    ]),
  );

  return (
    <div className="absolute bottom-3 right-3 z-20 hidden w-[184px] overflow-hidden rounded-lg border border-white/10 bg-[#05070f]/80 shadow-[0_16px_40px_rgba(0,0,0,0.4)] backdrop-blur-md sm:block">
      <div className="flex items-center justify-between border-b border-white/8 px-2.5 py-1.5">
        <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-foreground/35">Scene index</span>
        <span className="font-mono text-[11px] text-foreground/20">top / xz</span>
      </div>
      <div className="relative h-[104px] overflow-hidden bg-[radial-gradient(circle_at_50%_42%,rgba(121,232,255,0.08),transparent_62%)]">
        <div
          className="absolute inset-0 opacity-40"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.055) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.055) 1px, transparent 1px)",
            backgroundSize: "18px 18px",
          }}
          aria-hidden="true"
        />
        <div className="absolute inset-x-0 top-1/2 h-px bg-white/[0.06]" aria-hidden="true" />
        <div className="absolute inset-y-0 left-1/2 w-px bg-white/[0.06]" aria-hidden="true" />
        <span className="absolute left-2 top-1.5 font-mono text-[11px] text-foreground/20">N</span>

        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          className="pointer-events-none absolute inset-0 h-full w-full"
          aria-hidden="true"
        >
          {scene.relations.map((relation, index) => {
            const from = points.get(relation.subject_id);
            const to = points.get(relation.object_id);
            if (!from || !to) return null;
            const active =
              selectedId === relation.subject_id || selectedId === relation.object_id;
            return (
              <line
                key={`${relation.subject_id}-${relation.relation}-${relation.object_id}-${index}`}
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke={active ? "rgba(121,232,255,0.55)" : "rgba(255,255,255,0.13)"}
                strokeWidth={active ? 0.8 : 0.45}
                strokeDasharray={active ? undefined : "1.5 2"}
                vectorEffect="non-scaling-stroke"
              />
            );
          })}
        </svg>

        {entities.map((entity) => {
          const left = project(entity.transform.position[0], minX, maxX);
          const top = 100 - project(entity.transform.position[2], minZ, maxZ);
          const active = entity.id === selectedId;
          const size = entity.role === "subject" ? 9 : 7;
          return (
            <button
              key={entity.id}
              type="button"
              onClick={() => onSelect(active ? null : entity.id)}
              aria-label={`Select ${entity.label}, ${entityKindLabel(entity.kind)}`}
              aria-pressed={active}
              title={`${entity.label} · ${entityKindLabel(entity.kind)}`}
              className="absolute grid -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full transition-transform hover:scale-125 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-glow/80"
              style={{ left: `${left}%`, top: `${top}%`, width: 20, height: 20 }}
            >
              <span
                className={`block rounded-full border ${
                  active ? "border-white ring-2 ring-accent-glow/70" : "border-white/25"
                }`}
                style={{ width: size, height: size, backgroundColor: entityColor(entity) }}
              />
            </button>
          );
        })}
      </div>
      <div className="border-t border-white/8 px-2.5 py-1.5">
        <p className="truncate text-[11px] text-foreground/45">
          {selected ? `${selected.label} · ${entityKindLabel(selected.kind)}` : `${entities.length} elements · ${scene.relations.length} relations`}
        </p>
      </div>
    </div>
  );
}
