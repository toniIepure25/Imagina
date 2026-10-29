"use client";

import HudLabel from "@/components/system/HudLabel";
import SectionRule from "@/components/system/SectionRule";
import Surface from "@/components/system/Surface";
import type { SceneGraph } from "@/lib/animusStudioApi";
import type { WorldSpec } from "@/lib/imagine/world";

function label(value: string): string {
  return value.replace(/_/g, " ");
}

export default function SceneRead({ scene }: { scene: SceneGraph }) {
  const world = scene.metadata.world as WorldSpec | undefined;
  if (!world) return null;

  return (
    <Surface tone="stage" className="w-[286px] p-3.5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <HudLabel>Scene read</HudLabel>
          <h3 className="mt-1 truncate font-display text-lg leading-tight text-lumen-bone">{scene.title}</h3>
        </div>
        <span className="mt-0.5 shrink-0 font-mono text-[9px] uppercase tracking-[0.16em] text-lumen-mint/70">
          L1 preview
        </span>
      </div>

      <p className="mt-2 text-[11px] leading-5 text-foreground/45">
        You enter a {label(world.mood)} {label(world.biome)} at {label(world.timeOfDay)}, with a{" "}
        {label(world.archetype)} held at the threshold. Every form comes from the written brief; the signals only
        tune light, haze, and pace.
      </p>

      <SectionRule label="World grammar" className="mt-3" />
      <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-2">
        {[
          ["Biome", world.biome],
          ["Archetype", world.archetype],
          ["Time", world.timeOfDay],
          ["Weather", world.weather],
        ].map(([term, value]) => (
          <div key={term}>
            <dt className="font-mono text-[9px] uppercase tracking-[0.16em] text-foreground/25">{term}</dt>
            <dd className="mt-0.5 truncate text-[11px] text-foreground/65">{label(value)}</dd>
          </div>
        ))}
      </dl>

      <div className="mt-3 flex items-center justify-between gap-2 border-t border-white/[0.07] pt-2.5">
        <span className="truncate font-mono text-[10px] text-foreground/30">
          focus · {world.focal.label}
        </span>
        <span className="shrink-0 font-mono text-[10px] tabular-nums text-foreground/30">
          {world.layers.length} layers · {scene.entities.length} forms
        </span>
      </div>
      <p className="mt-2 font-mono text-[9px] uppercase tracking-[0.14em] text-lumen-ember/65">
        symbolic composition · not generated imagery
      </p>
    </Surface>
  );
}
