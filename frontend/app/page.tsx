"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import ClaimBadge from "@/components/platform/ClaimBadge";
import BoundaryNote from "@/components/platform/BoundaryNote";
import { DEFAULT_SCENE_PARAMS } from "@/lib/feedbackMapping";
import { PLATFORM_BOUNDARY } from "@/lib/claims";

const DreamCorridorScene = dynamic(() => import("@/components/scene/DreamCorridorScene"), { ssr: false });

const LOOP = [
  ["01", "Self-report", "Vividness, effort, and relaxation anchors."],
  ["02", "Signal", "Simulated EEG-like series, replayed deterministically."],
  ["03", "Estimate", "Rule-based proxy state with explicit uncertainty."],
  ["04", "PID / IQI", "Experimental composites, never a clinical score."],
  ["05", "Curriculum", "Eight-level adaptive staircase with safety overrides."],
  ["06", "Feedback", "Procedural scene parameters, no image model."],
  ["07", "Report", "Local evidence, provenance, and boundaries."],
];

const MODES = [
  {
    index: "01",
    label: "Studio",
    href: "/animus",
    title: "Build a symbolic scene, version by version.",
    body: "Natural language becomes typed commands. Preview, compare, blink, branch, and read the event trace. Every version stays immutable.",
    action: "Open Studio",
  },
  {
    index: "02",
    label: "Research Console",
    href: "/session",
    title: "Run the closed loop and inspect the evidence.",
    body: "Start a session, watch the corridor adapt, replay it deterministically, and read a report that states what the data can and cannot support.",
    action: "Start a session",
  },
  {
    index: "03",
    label: "Lumen",
    href: "/animus/imagine",
    title: "Describe a world. Walk through it.",
    body: "A text brief and a signal vector compose a layered first-person world: terrain, architecture, weather, and light. The diffusion lane stays visibly offline until a worker is attached.",
    action: "Enter Lumen",
  },
];

export default function LandingPage() {
  return (
    <AppShell level={1} status="local only">
      <section className="relative flex min-h-[calc(100dvh-3.5rem)] flex-col overflow-hidden">
        <div className="pointer-events-none absolute inset-0 opacity-55" aria-hidden="true">
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
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-background via-background/88 to-background/25" aria-hidden="true" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-background to-transparent" aria-hidden="true" />

        <div className="relative z-10 mx-auto flex w-full max-w-[1500px] flex-1 items-center px-4 py-14 md:px-8 lg:py-20">
          <div className="grid w-full gap-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.65fr)] lg:items-end">
            <div className="max-w-3xl">
              <div className="flex flex-wrap items-center gap-2">
                <span className="mono-label text-accent-glow/75">Local-first research instrument</span>
                <ClaimBadge />
              </div>
              <h1 className="mt-5 text-balance font-display text-5xl leading-[0.98] tracking-tight text-foreground sm:text-6xl lg:text-7xl">
                See the loop.
                <span className="block text-accent-glow">Change one variable.</span>
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-8 text-foreground/65 sm:text-lg">
                Three modes, one instrument: a spatial studio for composing symbolic scenes, a first-person world
                engine, and a research console for sessions, simulated signals, and evidence you can audit.
              </p>
              <div className="mt-8 flex flex-wrap gap-2.5">
                <Link
                  href="/animus"
                  className="inline-flex min-h-12 items-center rounded-lg bg-accent px-5 text-sm font-semibold text-white shadow-[0_0_32px_rgba(92,124,250,0.24)] transition-colors hover:bg-accent-glow hover:text-background"
                >
                  Open Studio
                </Link>
                <Link
                  href="/session"
                  className="inline-flex min-h-12 items-center rounded-lg border border-white/15 bg-white/[0.03] px-5 text-sm font-semibold text-foreground/80 transition-colors hover:border-accent-glow/40 hover:text-foreground"
                >
                  Start a session
                </Link>
                <Link
                  href="/science"
                  className="inline-flex min-h-12 items-center rounded-lg px-4 text-sm text-foreground/55 transition-colors hover:text-foreground"
                >
                  Read boundaries →
                </Link>
              </div>
              <div className="mt-9 grid max-w-xl grid-cols-3 gap-3 border-t border-white/10 pt-5">
                {[
                  ["26", "routes, one language"],
                  ["L1", "behavioral claim ceiling"],
                  ["0", "external services or telemetry"],
                ].map(([value, label]) => (
                  <div key={label}>
                    <p className="font-mono text-xl text-foreground/85">{value}</p>
                    <p className="mt-1 text-[11px] leading-4 text-foreground/40">{label}</p>
                  </div>
                ))}
              </div>
            </div>

            <aside className="hidden rounded-xl border border-white/12 bg-[#080a0d]/70 p-4 backdrop-blur-xl lg:block" aria-label="Instrument status">
              <div className="flex items-center justify-between">
                <span className="mono-label text-foreground/40">Instrument status</span>
                <span className="inline-flex items-center gap-1.5 font-mono text-[11px] text-signal/75">
                  <span className="h-1.5 w-1.5 rounded-full bg-signal" /> nominal
                </span>
              </div>
              <dl className="mt-4 space-y-3">
                {[
                  ["Studio", "symbolic scene graph · immutable versions"],
                  ["Session", "closed loop · safety monitor active"],
                  ["Replay", "deterministic · same seed, same stream"],
                  ["Evidence", "local SQLite · exportable"],
                ].map(([term, detail]) => (
                  <div key={term} className="border-b border-white/[0.07] pb-3 last:border-0 last:pb-0">
                    <dt className="text-sm text-foreground/80">{term}</dt>
                    <dd className="mt-0.5 text-[11px] leading-4 text-foreground/40">{detail}</dd>
                  </div>
                ))}
              </dl>
              <div className="mt-4 rounded-lg border border-lock/20 bg-lock/[0.05] p-2.5">
                <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-lock/70">Boundary</p>
                <p className="mt-1 text-[11px] leading-5 text-foreground/50">{PLATFORM_BOUNDARY}</p>
              </div>
            </aside>
          </div>
        </div>
      </section>

      <section className="border-t border-surface-border px-4 py-14 md:px-8" aria-labelledby="modes-title">
        <div className="mx-auto w-full max-w-[1500px]">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="mono-label text-accent-glow/65">One instrument, three modes</p>
              <h2 id="modes-title" className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
                Compose, walk, then measure.
              </h2>
            </div>
            <p className="max-w-xl text-sm leading-6 text-foreground/50">
              The Studio is for building and inspecting a scene. Lumen is for stepping inside a composed world. The
              Research Console runs the loop and records what happened. None of the three modes makes claims beyond the
              recorded evidence.
            </p>
          </div>
          <div className="mt-6 grid gap-4 lg:grid-cols-3">
            {MODES.map((mode) => (
              <Link
                key={mode.href}
                href={mode.href}
                className="group relative overflow-hidden rounded-xl border border-white/10 bg-white/[0.025] p-5 transition-colors hover:border-accent-glow/30 hover:bg-white/[0.04]"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="font-mono text-[11px] text-accent-glow/60">{mode.index}</span>
                  <span className="rounded-full border border-white/10 px-2 py-0.5 font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/40">
                    {mode.label}
                  </span>
                </div>
                <h3 className="mt-8 max-w-md text-2xl font-semibold leading-tight tracking-tight text-foreground/90">
                  {mode.title}
                </h3>
                <p className="mt-3 max-w-lg text-sm leading-6 text-foreground/50">{mode.body}</p>
                <span className="mt-6 inline-flex min-h-9 items-center text-sm text-accent-glow/85 group-hover:text-accent-glow">
                  {mode.action} →
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-surface-border px-4 py-14 md:px-8" aria-labelledby="loop-title">
        <div className="mx-auto w-full max-w-[1500px]">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="mono-label text-accent-glow/65">Closed loop</p>
              <h2 id="loop-title" className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
                Seven steps, each inspectable.
              </h2>
            </div>
            <p className="max-w-lg text-sm leading-6 text-foreground/50">
              The corridor is not a decoded mental image. It is an adaptive scaffold driven by experimental proxy
              metrics, with a safety monitor that can override the curriculum.
            </p>
          </div>
          <ol className="mt-6 grid gap-2 sm:grid-cols-2 lg:grid-cols-7">
            {LOOP.map(([number, title, detail]) => (
              <li key={number} className="rounded-lg border border-white/8 bg-white/[0.02] p-3">
                <span className="font-mono text-[11px] text-accent-glow/55">{number}</span>
                <h3 className="mt-2 text-sm font-medium text-foreground/80">{title}</h3>
                <p className="mt-1 text-[11px] leading-5 text-foreground/40">{detail}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="border-t border-surface-border px-4 py-14 md:px-8" aria-labelledby="boundaries-title">
        <div className="mx-auto grid w-full max-w-[1500px] gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <div className="rounded-xl border border-white/10 bg-white/[0.025] p-5">
            <p className="mono-label text-foreground/40">Allowed</p>
            <h2 id="boundaries-title" className="mt-2 text-2xl font-semibold tracking-tight text-foreground">
              What this instrument can say
            </h2>
            <ul className="mt-4 space-y-2.5 text-sm leading-6 text-foreground/60">
              {[
                "It estimates proxy metrics related to attention, self-reported vividness, behavioral stability, and simulated signal patterns.",
                "It adapts procedural visual feedback based on an estimated imagery state.",
                "It is a research prototype for closed-loop mental imagery training.",
                "PID and IQI are experimental proxies that still require validation.",
              ].map((item) => (
                <li key={item} className="flex gap-2.5">
                  <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-signal" aria-hidden="true" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-xl border border-lock/20 bg-lock/[0.045] p-5">
            <p className="mono-label text-lock/65">Not allowed</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">What it will never claim</h2>
            <ul className="mt-4 space-y-2.5 text-sm leading-6 text-foreground/60">
              {[
                "Read thoughts, decode dreams, or show what someone is imagining.",
                "Diagnose, treat, cure aphantasia, or guarantee lucid dreaming.",
                "Provide clinically validated neurofeedback or measure consciousness.",
              ].map((item) => (
                <li key={item} className="flex gap-2.5">
                  <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-lock" aria-hidden="true" />
                  {item}
                </li>
              ))}
            </ul>
            <Link href="/science" className="mt-5 inline-flex min-h-9 items-center text-sm text-lock/85 hover:text-lock">
              Read the full scientific boundary →
            </Link>
          </div>
        </div>
        <div className="mx-auto mt-5 w-full max-w-[1500px]">
          <BoundaryNote />
        </div>
      </section>
    </AppShell>
  );
}
