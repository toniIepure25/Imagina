"use client";

import { useId, useMemo } from "react";
import type { SceneEntity, SceneGraph } from "@/lib/animusStudioApi";
import { entityColor, entityKindLabel } from "./sceneUtils";

function shapeFor(kind: string): "subject" | "structure" | "light" | "object" {
  if (["castle", "building", "mountain", "tree", "city", "tower"].includes(kind)) return "structure";
  if (["moon", "sun", "star", "fire", "portal", "crystal", "light"].includes(kind)) return "light";
  if (["person", "dragon", "boat", "animal"].includes(kind)) return "subject";
  return "object";
}

function NodeShape({ entity, x, y }: { entity: SceneEntity; x: number; y: number }) {
  const color = entityColor(entity);
  const shape = shapeFor(entity.kind);
  if (shape === "structure") {
    return <rect x={x - 6} y={y - 6} width={12} height={12} rx={1.5} fill={color} opacity={0.9} />;
  }
  if (shape === "light") {
    return <path d={`M ${x} ${y - 7} L ${x + 7} ${y} L ${x} ${y + 7} L ${x - 7} ${y} Z`} fill={color} opacity={0.95} />;
  }
  return <circle cx={x} cy={y} r={shape === "subject" ? 5.5 : 4.2} fill={color} opacity={0.92} />;
}

export default function SceneSketch({
  scene,
  className = "",
  showLabels = false,
  ariaLabel,
}: {
  scene: SceneGraph;
  className?: string;
  showLabels?: boolean;
  ariaLabel?: string;
}) {
  const gradientId = useId().replace(/:/g, "");
  const layout = useMemo(() => {
    const entities = scene.entities;
    if (!entities.length) return { points: [] as Array<{ entity: SceneEntity; x: number; y: number }>, bounds: null };
    const xs = entities.map((entity) => entity.transform.position[0]);
    const zs = entities.map((entity) => entity.transform.position[2]);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minZ = Math.min(...zs);
    const maxZ = Math.max(...zs);
    const spanX = Math.max(1, maxX - minX);
    const spanZ = Math.max(1, maxZ - minZ);
    const points = entities.map((entity) => ({
      entity,
      x: 26 + ((entity.transform.position[0] - minX) / spanX) * 268,
      y: 24 + ((entity.transform.position[2] - minZ) / spanZ) * 132,
    }));
    return { points, bounds: { minX, maxX, minZ, maxZ } };
  }, [scene.entities]);

  const label = ariaLabel ?? `${scene.title}. ${scene.entities.length} symbolic elements and ${scene.relations.length} relations.`;

  return (
    <svg
      viewBox="0 0 320 180"
      role="img"
      aria-label={label}
      className={`h-full w-full ${className}`}
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={scene.atmosphere.sky.top} />
          <stop offset="58%" stopColor={scene.atmosphere.sky.horizon} />
          <stop offset="100%" stopColor={scene.atmosphere.sky.bottom} />
        </linearGradient>
        <pattern id={`${gradientId}-grid`} width="24" height="24" patternUnits="userSpaceOnUse">
          <path d="M 24 0 L 0 0 0 24" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="0.6" />
        </pattern>
      </defs>
      <rect width="320" height="180" fill={`url(#${gradientId})`} />
      <rect width="320" height="180" fill={`url(#${gradientId}-grid)`} opacity="0.7" />
      {scene.relations.map((relation, index) => {
        const from = layout.points.find((point) => point.entity.id === relation.subject_id);
        const to = layout.points.find((point) => point.entity.id === relation.object_id);
        if (!from || !to) return null;
        return (
          <line
            key={`${relation.subject_id}-${relation.relation}-${relation.object_id}-${index}`}
            x1={from.x}
            y1={from.y}
            x2={to.x}
            y2={to.y}
            stroke="rgba(232,226,212,0.38)"
            strokeWidth="0.9"
            strokeDasharray="3 3"
          />
        );
      })}
      {layout.points.map(({ entity, x, y }) => (
        <g key={entity.id}>
          <circle cx={x} cy={y} r={9} fill="rgba(0,0,0,0.22)" />
          <NodeShape entity={entity} x={x} y={y} />
          {showLabels && layout.points.length <= 8 ? (
            <text
              x={x + 8}
              y={y + 3}
              fill="rgba(255,255,255,0.82)"
              fontSize="11"
              fontFamily="ui-monospace, monospace"
            >
              {entity.label.slice(0, 18)}
            </text>
          ) : null}
        </g>
      ))}
      {layout.points.length === 0 ? (
        <text x="160" y="94" textAnchor="middle" fill="rgba(255,255,255,0.55)" fontSize="11">
          Empty stage
        </text>
      ) : null}
      <text x="12" y="170" fill="rgba(255,255,255,0.48)" fontSize="11" fontFamily="ui-monospace, monospace">
        {scene.style} · {scene.atmosphere.time_of_day} · {entityKindLabel(scene.entities[0]?.kind ?? "scene")}
      </text>
    </svg>
  );
}
