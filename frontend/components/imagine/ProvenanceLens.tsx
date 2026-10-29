"use client";

import type { SceneGraph } from "@/lib/animusStudioApi";
import type { ImagineConditioning, ImagineControls, ImagineManifest } from "@/lib/imagine/types";

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export default function ProvenanceLens({
  scene,
  conditioning,
  controls,
  manifest,
}: {
  scene: SceneGraph;
  conditioning: ImagineConditioning;
  controls: ImagineControls;
  manifest: ImagineManifest | null;
}) {
  return (
    <div className="space-y-3" data-testid="provenance-lens">
      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-foreground/35">Scene provenance</p>
        <dl className="mt-2 space-y-1.5 text-[11px]">
          <div className="flex justify-between gap-3">
            <dt className="text-foreground/40">Geometry</dt>
            <dd className="text-foreground/70">local procedural</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-foreground/40">Environment texture</dt>
            <dd className={manifest ? "text-signal" : "text-foreground/55"}>
              {manifest ? "diffusion-backed skybox" : "procedural sky"}
            </dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-foreground/40">Conditioning</dt>
            <dd className="font-mono text-foreground/60">{conditioning.vectorHash}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-foreground/40">Quality gate</dt>
            <dd className="text-foreground/60">{percent(conditioning.vector.signal_quality)}</dd>
          </div>
          {manifest ? (
            <>
              <div className="flex justify-between gap-3">
                <dt className="text-foreground/40">Model</dt>
                <dd className="font-mono text-foreground/60">{manifest.model_slot}</dd>
              </div>
              <div className="flex justify-between gap-3">
                <dt className="text-foreground/40">Seed</dt>
                <dd className="font-mono text-foreground/60">{manifest.seed}</dd>
              </div>
            </>
          ) : null}
        </dl>
      </div>

      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-foreground/35">Aesthetic controls</p>
        <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1.5 font-mono text-[11px]">
          {Object.entries(controls).map(([key, value]) => (
            <div key={key} className="flex justify-between gap-2">
              <span className="text-foreground/40">{key}</span>
              <span className="text-foreground/65">{percent(value)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-foreground/35">Elements</p>
        <ul className="mt-2 space-y-1.5">
          {scene.entities.slice(0, 8).map((entity) => (
            <li key={entity.id} className="flex items-center justify-between gap-2 text-[11px]">
              <span className="truncate text-foreground/60">{entity.label}</span>
              <span className="shrink-0 font-mono text-foreground/30">{entity.provenance}</span>
            </li>
          ))}
        </ul>
      </div>

      <p className="text-[11px] leading-5 text-foreground/35">
        Text sets the scene. Signals tune atmosphere. No thought decoding, imagery reconstruction, or diagnosis.
      </p>
    </div>
  );
}
