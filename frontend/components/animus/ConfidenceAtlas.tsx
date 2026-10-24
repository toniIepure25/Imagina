"use client";

import type { EvidenceItem, Observatory, SceneGraph } from "@/lib/animusStudioApi";

const PROVENANCE_COLOR: Record<string, string> = {
  direct_probe: "#7dd3fc",
  prior: "#a1a1aa",
  abstained: "#fbbf24",
  mixed: "#c084fc",
};

function parseVariable(variableId: string): { kind: string; subject: string; object?: string } {
  const parts = variableId.split(":");
  if (parts[0] === "rel" && parts.length >= 4) {
    return { kind: "relation", subject: parts[1], object: parts[2] };
  }
  if (parts[0] === "obj" && parts.length >= 2) {
    return { kind: "object", subject: parts[1] };
  }
  return { kind: "decoy", subject: variableId };
}

function normalize(value: number, values: number[]): number {
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (!Number.isFinite(min) || !Number.isFinite(max) || max - min < 1e-6) return 0.5;
  return (value - min) / (max - min);
}

function AtlasMap({ scene, evidence }: { scene: SceneGraph; evidence: EvidenceItem[] }) {
  const entities = scene.entities;
  const xs = entities.map((entity) => entity.transform.position[0]);
  const zs = entities.map((entity) => entity.transform.position[2]);
  const entityById = new Map(entities.map((entity) => [entity.id, entity]));
  const placed = evidence.map((item, index) => {
    const parsed = parseVariable(item.variable_id);
    const entity = entityById.get(parsed.subject);
    if (!entity) {
      return { item, x: 24 + (index % 4) * 78, y: 18 };
    }
    return {
      item,
      x: 24 + normalize(entity.transform.position[0], xs) * 252,
      y: 104 - normalize(entity.transform.position[2], zs) * 82,
    };
  });
  const lines = evidence.flatMap((item) => {
    const parsed = parseVariable(item.variable_id);
    if (parsed.kind !== "relation" || !parsed.object) return [];
    const subject = entityById.get(parsed.subject);
    const object = entityById.get(parsed.object);
    if (!subject || !object) return [];
    return [{
      key: item.variable_id,
      x1: 24 + normalize(subject.transform.position[0], xs) * 252,
      y1: 104 - normalize(subject.transform.position[2], zs) * 82,
      x2: 24 + normalize(object.transform.position[0], xs) * 252,
      y2: 104 - normalize(object.transform.position[2], zs) * 82,
    }];
  });

  return (
    <svg
      viewBox="0 0 300 128"
      role="img"
      aria-label="Top-down confidence atlas of reconstructed scene features"
      className="h-auto w-full rounded-xl border border-white/10 bg-[#070a12]"
    >
      {lines.map((line) => (
        <line
          key={line.key}
          x1={line.x1}
          y1={line.y1}
          x2={line.x2}
          y2={line.y2}
          stroke="rgba(255,255,255,0.16)"
          strokeWidth="1"
        />
      ))}
      {placed.map(({ item, x, y }) => (
        <g key={item.variable_id}>
          <circle
            cx={x}
            cy={y}
            r={4 + item.uncertainty * 5}
            fill={PROVENANCE_COLOR[item.provenance] ?? "#a1a1aa"}
            fillOpacity={0.35 + item.posterior * 0.5}
            stroke="rgba(255,255,255,0.45)"
          />
          <text x={x + 7} y={y + 3} fill="rgba(255,255,255,0.62)" fontSize="6">
            {item.label.slice(0, 18)}
          </text>
        </g>
      ))}
      {placed.length === 0 ? (
        <text x="150" y="66" textAnchor="middle" fill="rgba(255,255,255,0.35)" fontSize="8">
          No mapped evidence yet
        </text>
      ) : null}
    </svg>
  );
}

export default function ConfidenceAtlas({
  observatory,
  scene,
}: {
  observatory: Observatory;
  scene: SceneGraph;
}) {
  const evidence = observatory.evidence ?? [];
  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-medium">Confidence atlas</h2>
        <span className="text-[11px] text-foreground/35">
          {evidence.length} feature{evidence.length === 1 ? "" : "s"} · belief layer
        </span>
      </div>
      <p className="mt-1 text-xs leading-relaxed text-foreground/45">
        Position is a top-down sketch of the scene. Colour is provenance, opacity is posterior, and
        radius is uncertainty. This is a descriptive map, not a neural image.
      </p>
      <div className="mt-4">
        <AtlasMap scene={scene} evidence={evidence} />
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[560px] text-left text-xs">
          <caption className="sr-only">Accessible tabular view of the confidence atlas</caption>
          <thead className="text-[10px] uppercase tracking-[0.14em] text-foreground/35">
            <tr>
              <th className="pb-2 pr-3 font-normal">Feature</th>
              <th className="pb-2 pr-3 font-normal">Provenance</th>
              <th className="pb-2 pr-3 font-normal">Posterior</th>
              <th className="pb-2 pr-3 font-normal">Uncertainty</th>
              <th className="pb-2 pr-3 font-normal">Sources</th>
              <th className="pb-2 font-normal">Leave-one-out</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {evidence.map((item) => (
              <tr key={item.variable_id}>
                <td className="py-2 pr-3 text-foreground/80">{item.label}</td>
                <td className="py-2 pr-3 text-foreground/55">{item.provenance.replace(/_/g, " ")}</td>
                <td className="py-2 pr-3 tabular-nums text-foreground/75">
                  {Math.round(item.posterior * 100)}%
                </td>
                <td className="py-2 pr-3 tabular-nums text-foreground/55">
                  {Math.round(item.uncertainty * 100)}%
                </td>
                <td className="py-2 pr-3 tabular-nums text-foreground/55">{item.n_sources}</td>
                <td className="py-2 tabular-nums text-foreground/55">
                  {item.leave_one_out_delta.toFixed(3)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {evidence.length === 0 ? (
          <p className="py-3 text-xs text-foreground/40">Complete an epistemic interview first.</p>
        ) : null}
      </div>
    </section>
  );
}
