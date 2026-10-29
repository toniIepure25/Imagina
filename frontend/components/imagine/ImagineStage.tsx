"use client";

import dynamic from "next/dynamic";
import {
  useMemo,
  useRef,
  useState,
  type MutableRefObject,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { buttonStyles } from "@/components/common/Button";
import SceneRead from "@/components/imagine/SceneRead";
import { describeImagineScene, type ImagineSignals, type ImagineStyle } from "@/lib/imagineScene";
import type { SceneGraph } from "@/lib/animusStudioApi";

const AnimusScene = dynamic(() => import("@/components/animus/AnimusScene"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[52vh] items-center justify-center bg-[#050711]" role="status">
      <div className="text-center">
        <div className="mx-auto h-10 w-10 animate-pulse rounded-full border border-dashed border-signal/40" />
        <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.16em] text-foreground/40">
          Loading first-person stage
        </p>
      </div>
    </div>
  ),
});

function VirtualJoystick({ onChange }: { onChange: (value: { x: number; y: number }) => void }) {
  const [knob, setKnob] = useState({ x: 0, y: 0 });
  const active = useRef(false);
  const origin = useRef({ x: 0, y: 0 });

  const update = (event: ReactPointerEvent<HTMLDivElement>) => {
    const dx = event.clientX - origin.current.x;
    const dy = event.clientY - origin.current.y;
    const radius = 38;
    const length = Math.hypot(dx, dy);
    const scale = length > radius ? radius / length : 1;
    const next = { x: (dx * scale) / radius, y: (-dy * scale) / radius };
    setKnob({ x: dx * scale, y: dy * scale });
    onChange(next);
  };

  const stop = (event: ReactPointerEvent<HTMLDivElement>) => {
    active.current = false;
    setKnob({ x: 0, y: 0 });
    onChange({ x: 0, y: 0 });
    event.currentTarget.releasePointerCapture?.(event.pointerId);
  };

  return (
    <div
      data-testid="imagine-joystick"
      aria-label="Touch movement pad"
      role="application"
      className="pointer-events-auto absolute bottom-24 left-4 z-20 flex h-24 w-24 touch-none items-center justify-center rounded-full border border-white/15 bg-[#05060c]/55 backdrop-blur md:hidden"
      onPointerDown={(event) => {
        event.preventDefault();
        active.current = true;
        const rect = event.currentTarget.getBoundingClientRect();
        origin.current = { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
        event.currentTarget.setPointerCapture?.(event.pointerId);
        update(event);
      }}
      onPointerMove={(event) => {
        if (active.current) update(event);
      }}
      onPointerUp={stop}
      onPointerCancel={stop}
    >
      <span
        className="pointer-events-none block h-10 w-10 rounded-full border border-signal/40 bg-signal/15"
        style={{ transform: `translate(${knob.x}px, ${knob.y}px)` }}
      />
    </div>
  );
}

export default function ImagineStage({
  scene,
  firstPerson,
  style,
  signals,
  onToggleFirstPerson,
  environmentTextureUrl = null,
  collisionEnabled = true,
  movementRef,
  diffusionState = "offline",
}: {
  scene: SceneGraph;
  firstPerson: boolean;
  style: ImagineStyle;
  signals: ImagineSignals;
  onToggleFirstPerson: () => void;
  environmentTextureUrl?: string | null;
  collisionEnabled?: boolean;
  movementRef?: MutableRefObject<{ x: number; y: number }>;
  diffusionState?: "offline" | "generated";
}) {
  const description = useMemo(() => describeImagineScene(scene), [scene]);
  const [lens, setLens] = useState<"scene" | "signals" | "off">("scene");
  const [coach, setCoach] = useState(true);
  const hasWorld = Boolean(scene.metadata.world);

  return (
    <div className="relative h-full min-h-[52vh] w-full overflow-hidden bg-[#050711]" data-testid="imagine-stage">
      <AnimusScene
        scene={scene}
        selectedId={null}
        onSelect={() => undefined}
        className="h-full w-full"
        dpr={[1, 1.5]}
        showOverlay={false}
        interactive={!firstPerson}
        readOnly={firstPerson}
        cameraMode={firstPerson ? "firstPerson" : "orbit"}
        description={description}
        onExitFirstPerson={onToggleFirstPerson}
        firstPersonLookMode="pointer"
        collisionEnabled={collisionEnabled}
        movementRef={movementRef}
        environmentTextureUrl={environmentTextureUrl}
      />

      <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex items-start justify-between gap-3 bg-gradient-to-b from-[#05060c]/80 via-[#05060c]/20 to-transparent p-3 sm:p-4">
        <div className="min-w-0">
          <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-signal/70">first-person preview</p>
          <h2 className="mt-1 truncate font-display text-base text-foreground/90 sm:text-lg">{scene.title}</h2>
          <p className="mt-1 font-mono text-[11px] text-foreground/40">
            {scene.entities.length} symbolic elements · {style} · seed {scene.seed.toString(16)}
          </p>
          <div className="pointer-events-auto mt-2.5 flex items-center gap-1" role="group" aria-label="Stage lens">
            {(["scene", "signals", "off"] as const).map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={lens === option}
                onClick={() => setLens(option)}
                className={`min-h-8 rounded-sm border px-2 font-mono text-[9px] uppercase tracking-[0.14em] backdrop-blur transition-colors ${
                  lens === option
                    ? "border-lumen-mint/35 bg-lumen-mint/[0.08] text-lumen-mint/85"
                    : "border-white/10 bg-black/20 text-foreground/35 hover:text-foreground/70"
                }`}
              >
                {option}
              </button>
            ))}
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <span className="rounded-full border border-signal/30 bg-[#071411]/80 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.14em] text-signal/85 backdrop-blur">
            local procedural
          </span>
          <span
            className={`rounded-full border px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.14em] backdrop-blur ${
              diffusionState === "generated"
                ? "border-signal/30 bg-[#071411]/80 text-signal/85"
                : "border-white/10 bg-background/70 text-foreground/45"
            }`}
          >
            {diffusionState === "generated" ? "diffusion skybox" : "diffusion offline"}
          </span>
        </div>
      </div>

      {lens === "scene" && hasWorld ? (
        <div className="pointer-events-none absolute right-3 top-[128px] z-10 hidden lg:block">
          <div className="pointer-events-auto">
            <SceneRead scene={scene} />
          </div>
        </div>
      ) : null}

      {lens === "signals" ? (
        <div className="pointer-events-none absolute left-3 top-1/2 z-10 hidden -translate-y-1/2 flex-col gap-2 sm:flex">
          {[
            ["ATT", signals.attention],
            ["ARO", signals.arousal],
            ["VAL", signals.valence],
            ["VIV", signals.vividness],
          ].map(([label, value]) => (
            <div key={label as string} className="flex items-center gap-2 font-mono text-[9px] text-foreground/40">
              <span className="w-7">{label}</span>
              <span className="h-px w-14 overflow-hidden bg-white/15">
                <span
                  className="block h-full bg-lumen-mint/80"
                  style={{ width: `${Math.round(Number(value) * 100)}%` }}
                />
              </span>
              <span className="w-6 tabular-nums text-foreground/25">{Math.round(Number(value) * 100)}</span>
            </div>
          ))}
        </div>
      ) : null}

      <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 flex items-end justify-between gap-3 bg-gradient-to-t from-[#05060c]/90 via-[#05060c]/30 to-transparent p-3 sm:p-4">
        <div className="min-w-0">
          <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-foreground/35">
            {firstPerson ? "Click to lock · WASD move · R reset · F exit" : "drag orbit · scroll zoom"}
          </p>
          <p className="mt-1 max-w-md font-mono text-[11px] leading-5 text-foreground/30">
            Symbolic geometry, not generated imagery. Signal values are a demo control surface.
          </p>
        </div>
        <button
          type="button"
          onClick={onToggleFirstPerson}
          className={buttonStyles({
            variant: "secondary",
            size: "sm",
            className:
              "pointer-events-auto min-h-11 shrink-0 border-white/15 bg-background/70 px-3 font-mono text-[11px] uppercase tracking-[0.12em] backdrop-blur hover:border-signal/40",
          })}
        >
          {firstPerson ? "Exit first person" : "Enter first person"}
        </button>
      </div>

      {firstPerson ? (
        <div className="pointer-events-none absolute left-1/2 top-1/2 z-10 -translate-x-1/2 -translate-y-1/2" aria-hidden="true">
          <span className="block h-5 w-5 rounded-full border border-white/35 shadow-[0_0_18px_rgba(255,255,255,0.18)]" />
          <span className="absolute left-1/2 top-1/2 block h-1 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/80" />
          <span className="absolute left-1/2 top-[-7px] h-2 w-px -translate-x-1/2 bg-white/40" />
          <span className="absolute bottom-[-7px] left-1/2 h-2 w-px -translate-x-1/2 bg-white/40" />
          <span className="absolute left-[-7px] top-1/2 h-px w-2 -translate-y-1/2 bg-white/40" />
          <span className="absolute right-[-7px] top-1/2 h-px w-2 -translate-y-1/2 bg-white/40" />
        </div>
      ) : null}

      {firstPerson && movementRef ? <VirtualJoystick onChange={(value) => (movementRef.current = value)} /> : null}

      {coach ? (
        <div className="pointer-events-none absolute bottom-[92px] left-1/2 z-20 hidden -translate-x-1/2 sm:block">
          <div className="pointer-events-auto flex items-center gap-3 rounded-sm border border-white/10 bg-[#070b12]/88 px-3 py-2 shadow-2xl backdrop-blur">
            <span className="h-1.5 w-1.5 rounded-full bg-lumen-mint shadow-[0_0_10px_rgba(136,240,214,0.9)]" />
            <p className="font-mono text-[10px] tracking-[0.02em] text-foreground/55">
              Click the stage to look · <span className="text-foreground/80">W A S D</span> to walk ·{" "}
              <span className="text-foreground/80">F</span> to leave
            </p>
            <button
              type="button"
              onClick={() => setCoach(false)}
              className="min-h-7 rounded-sm border border-white/10 px-2 font-mono text-[9px] uppercase tracking-[0.14em] text-foreground/35 transition-colors hover:text-foreground/70"
            >
              Got it
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
