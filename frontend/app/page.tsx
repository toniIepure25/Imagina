"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { DEFAULT_SCENE_PARAMS } from "@/lib/feedbackMapping";

const DreamCorridorScene = dynamic(() => import("@/components/scene/DreamCorridorScene"), { ssr: false });

const LOOP = [
  "Self-report",
  "Simulated signal",
  "State estimate",
  "PID / IQI",
  "Curriculum",
  "Scene feedback",
  "Report",
];

export default function LandingPage() {
  return (
    <main className="flex-1">
      <section className="relative min-h-[calc(100vh-96px)] overflow-hidden">
        <div className="absolute inset-0 opacity-75">
          <DreamCorridorScene
            params={{
              ...DEFAULT_SCENE_PARAMS,
              clarity: 0.72,
              fogDensity: 0.24,
              lightStability: 0.82,
              textureDetail: 0.68,
              particleStability: 0.74,
              doorComplexity: 0.55,
              colorSaturation: 0.78,
              breathingCueStrength: 0.18,
              wallDistortion: 0.12,
              blur: 0.06,
            }}
          />
        </div>
        <div className="absolute inset-0 bg-gradient-to-r from-background via-background/76 to-background/20" />
        <div className="relative z-20 flex min-h-[calc(100vh-96px)] max-w-7xl flex-col justify-center px-6 py-16">
          <div className="max-w-3xl space-y-7">
            <div className="text-[11px] uppercase tracking-[0.28em] text-accent-glow/80">
              Local-first closed-loop research prototype
            </div>
            <h1 className="text-5xl font-bold tracking-tight glow-text sm:text-7xl">
              IMAGINA <span className="text-accent-glow">V2</span>
            </h1>
            <p className="text-2xl text-foreground/78">Dream Corridor Scene Stabilizer</p>
            <p className="max-w-2xl text-base leading-8 text-foreground/68">
              A local-first closed-loop prototype for training visual mental imagery stability using
              self-report, behavioral proxies, and simulated EEG-like feedback.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/session" className="rounded-lg bg-accent px-6 py-3 font-semibold text-white shadow-[0_0_28px_rgba(91,108,255,0.28)] transition-all hover:bg-accent-glow hover:text-background">
                Start Session
              </Link>
              <Link href="/replay" className="rounded-lg border border-surface-border px-6 py-3 font-semibold text-foreground/82 transition-all hover:border-accent/60 hover:bg-surface">
                Watch Replay
              </Link>
              <Link href="/science" className="rounded-lg border border-surface-border px-6 py-3 font-semibold text-foreground/70 transition-all hover:border-accent/60 hover:bg-surface">
                Read Scientific Notes
              </Link>
            </div>
            <p className="max-w-2xl text-xs leading-6 text-foreground/42">
              IMAGINA does not read thoughts, decode dreams, diagnose or treat conditions, cure aphantasia,
              guarantee lucid dreaming, or measure consciousness objectively. PID and IQI are experimental proxy metrics.
            </p>
          </div>
        </div>
      </section>

      <section className="px-6 py-14">
        <div className="mx-auto grid max-w-6xl gap-4 lg:grid-cols-2">
          <div className="glass p-6 panel-glow">
            <h2 className="mb-4 text-xl font-semibold text-accent-glow">What it does</h2>
            <div className="grid gap-3 text-sm text-foreground/68 sm:grid-cols-2">
              <p>Estimates proxy metrics for imagery stability and engagement.</p>
              <p>Adapts a procedural Dream Corridor scene in real time.</p>
              <p>Guides mental imagery practice through an 8-level curriculum.</p>
              <p>Logs local sessions and produces replayable reports.</p>
            </div>
          </div>
          <div className="glass p-6 panel-glow">
            <h2 className="mb-4 text-xl font-semibold text-danger">What it does not do</h2>
            <div className="grid gap-3 text-sm text-foreground/68 sm:grid-cols-2">
              <p>Does not read thoughts or decode dreams.</p>
              <p>Does not show what a person is imagining.</p>
              <p>Does not diagnose, treat, or provide medical advice.</p>
              <p>Does not measure consciousness objectively.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 pb-16">
        <div className="mx-auto max-w-6xl">
          <div className="mb-5 text-[11px] uppercase tracking-[0.24em] text-accent-glow/70">System Loop</div>
          <div className="grid gap-3 md:grid-cols-7">
            {LOOP.map((item, index) => (
              <div key={item} className="glass panel-glow p-4">
                <div className="mb-2 font-mono text-xs text-accent-glow">{String(index + 1).padStart(2, "0")}</div>
                <div className="text-sm font-medium text-foreground/82">{item}</div>
              </div>
            ))}
          </div>
          <p className="mt-6 max-w-3xl text-sm text-foreground/50">
            The corridor is not a decoded mental image. It is an adaptive scaffold driven by experimental proxy metrics.
          </p>
        </div>
      </section>
    </main>
  );
}
