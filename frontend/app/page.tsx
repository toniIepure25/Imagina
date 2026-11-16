"use client";

import Image from "next/image";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import ClaimBadge from "@/components/platform/ClaimBadge";
import BoundaryNote from "@/components/platform/BoundaryNote";

const LOOP = [
  ["01", "Intend", "Write the scene you want to inspect, in ordinary language."],
  ["02", "Stage", "See a deterministic symbolic candidate before committing to it."],
  ["03", "Correct", "Move, lock, rename, or reject one thing at a time."],
  ["04", "Compare", "Read the version graph and the changes that produced it."],
  ["05", "Record", "Export the session, its provenance, and its stated limits."],
];

const SURFACES = [
  {
    index: "01",
    label: "Studio",
    href: "/animus",
    title: "A scene graph you can inspect and revise.",
    body: "Describe an intention, stage a candidate, correct what is wrong, and keep every version immutable. The scene is symbolic and editable — not a generated image.",
    action: "Open ANIMUS",
  },
  {
    index: "02",
    label: "Lumen",
    href: "/animus/imagine",
    title: "A first-person world, composed from a brief.",
    body: "Terrain, architecture, weather, and light are assembled from a text brief and a conditioning vector. The diffusion lane fails closed until a worker is explicitly attached.",
    action: "Enter Lumen",
  },
  {
    index: "03",
    label: "Evidence",
    href: "/science",
    title: "Claims that travel with their limits.",
    body: "The registry records what is simulated, what is measured, what is blocked, and what the instrument is not allowed to say. Start with the boundary, not the demo.",
    action: "Read the evidence",
  },
];

export default function LandingPage() {
  return (
    <AppShell level={1} status="local only">
      <section className="relative overflow-hidden border-b border-white/8">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_20%_0%,rgba(92,124,250,0.16),transparent_55%),radial-gradient(ellipse_at_90%_20%,rgba(232,180,90,0.08),transparent_45%)]" aria-hidden="true" />
        <div className="relative mx-auto grid w-full max-w-[1500px] gap-12 px-4 py-16 md:px-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(360px,0.75fr)] lg:items-center lg:py-24">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="mono-label text-accent-glow/75">Local-first research instrument</span>
              <ClaimBadge />
            </div>
            <h1 className="mt-5 text-balance font-display text-5xl leading-[0.98] tracking-tight text-foreground sm:text-6xl lg:text-7xl">
              Make imagination
              <span className="block text-accent-glow">inspectable.</span>
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-8 text-foreground/65 sm:text-lg">
              ANIMUS is a local-first workspace for composing symbolic scenes, testing what changed, and
              keeping every version, decision, and uncertainty boundary on your own machine. No account.
              No telemetry. No neural decoding.
            </p>
            <div className="mt-8 flex flex-wrap gap-2.5">
              <Link
                href="/animus"
                className="inline-flex min-h-12 items-center rounded-lg bg-accent px-5 text-sm font-semibold text-white shadow-[0_0_32px_rgba(92,124,250,0.24)] transition-colors hover:bg-accent-glow hover:text-background"
              >
                Open ANIMUS
              </Link>
              <Link
                href="/science"
                className="inline-flex min-h-12 items-center rounded-lg border border-white/15 bg-white/[0.03] px-5 text-sm font-semibold text-foreground/80 transition-colors hover:border-accent-glow/40 hover:text-foreground"
              >
                Explore the evidence
              </Link>
              <Link
                href="#for-labs"
                className="inline-flex min-h-12 items-center rounded-lg px-4 text-sm text-foreground/55 transition-colors hover:text-foreground"
              >
                For labs →
              </Link>
            </div>
            <div className="mt-9 grid max-w-xl grid-cols-3 gap-3 border-t border-white/10 pt-5">
              {[
                ["Local", "SQLite and your files"],
                ["0", "accounts or telemetry"],
                ["L1", "behavioural claim ceiling"],
              ].map(([value, label]) => (
                <div key={label}>
                  <p className="font-mono text-xl text-foreground/85">{value}</p>
                  <p className="mt-1 text-[11px] leading-4 text-foreground/40">{label}</p>
                </div>
              ))}
            </div>
          </div>

          <figure className="relative">
            <div className="relative aspect-[4/3] overflow-hidden rounded-xl border border-white/12 bg-[#080a0d] shadow-[0_24px_80px_rgba(0,0,0,0.45)]">
              <Image
                src="/animus/studio.png"
                alt="ANIMUS Studio: a symbolic scene graph with an immutable version ledger"
                fill
                priority
                sizes="(min-width: 1024px) 42vw, 100vw"
                className="object-cover"
              />
            </div>
            <figcaption className="mt-3 flex flex-wrap items-center justify-between gap-2 text-[11px] text-foreground/40">
              <span>ANIMUS Studio — symbolic scene graph, immutable versions</span>
              <span className="font-mono uppercase tracking-[0.18em]">local · experimental</span>
            </figcaption>
          </figure>
        </div>
      </section>

      <section className="mx-auto w-full max-w-[1500px] px-4 py-16 md:px-8 lg:py-20">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,0.55fr)_minmax(0,1fr)]">
          <div>
            <span className="mono-label text-foreground/40">The loop</span>
            <h2 className="mt-3 text-balance font-display text-3xl leading-tight text-foreground sm:text-4xl">
              One loop. Every step inspectable.
            </h2>
            <p className="mt-4 max-w-md text-sm leading-7 text-foreground/55">
              The product is not a one-shot prompt. It is a versioned, reversible loop between intention
              and inspection — designed for research, not for spectacle.
            </p>
          </div>
          <ol className="divide-y divide-white/8 border-y border-white/8">
            {LOOP.map(([index, title, body]) => (
              <li key={index} className="grid gap-2 py-4 sm:grid-cols-[3rem_minmax(0,0.42fr)_minmax(0,1fr)] sm:items-baseline">
                <span className="font-mono text-xs text-accent-glow/70">{index}</span>
                <span className="text-sm font-medium text-foreground/85">{title}</span>
                <span className="text-sm leading-6 text-foreground/50">{body}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="border-y border-white/8 bg-white/[0.015]">
        <div className="mx-auto w-full max-w-[1500px] px-4 py-16 md:px-8 lg:py-20">
          <div className="flex flex-wrap items-end justify-between gap-6">
            <div>
              <span className="mono-label text-foreground/40">Three surfaces</span>
              <h2 className="mt-3 font-display text-3xl leading-tight text-foreground sm:text-4xl">
                Compose. Walk. Audit.
              </h2>
            </div>
            <p className="max-w-md text-sm leading-6 text-foreground/50">
              The same local backend, the same provenance, and the same claim boundary across three
              different ways of working with a scene.
            </p>
          </div>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {SURFACES.map((surface) => (
              <Link
                key={surface.label}
                href={surface.href}
                className="group flex min-h-64 flex-col rounded-xl border border-white/10 bg-[#080a0d]/70 p-5 transition-colors hover:border-accent-glow/35"
              >
                <div className="flex items-center justify-between">
                  <span className="mono-label text-foreground/35">{surface.index}</span>
                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent-glow/60">{surface.label}</span>
                </div>
                <h3 className="mt-5 text-balance font-display text-2xl leading-tight text-foreground/90">{surface.title}</h3>
                <p className="mt-3 flex-1 text-sm leading-6 text-foreground/50">{surface.body}</p>
                <span className="mt-5 inline-flex items-center text-sm text-accent-glow/80 transition-colors group-hover:text-accent-glow">
                  {surface.action} →
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-[1500px] gap-10 px-4 py-16 md:px-8 lg:grid-cols-2 lg:py-20">
        <div className="rounded-xl border border-white/10 bg-[#080a0d]/70 p-6">
          <span className="mono-label text-foreground/40">What this is</span>
          <ul className="mt-5 space-y-3 text-sm leading-6 text-foreground/65">
            {[
              "A local-first instrument for symbolic scene authoring, correction, and comparison.",
              "A provenance-aware record of versions, events, exports, and stated limits.",
              "A research surface for behavioural tasks that separates what was observed from what was inferred.",
            ].map((item) => (
              <li key={item} className="flex gap-2.5">
                <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-signal" aria-hidden="true" />
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl border border-white/10 bg-[#080a0d]/70 p-6">
          <span className="mono-label text-foreground/40">What this is not</span>
          <ul className="mt-5 space-y-3 text-sm leading-6 text-foreground/65">
            {[
              "Not an image generator, neural reconstruction system, or decoder of imagined content.",
              "Not a clinical diagnostic, treatment, neurofeedback, or BCI product.",
              "Not a validated measure of imagination ability, and not a consciousness claim.",
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
      </section>

      <section id="for-labs" className="border-t border-white/8 bg-[linear-gradient(180deg,rgba(92,124,250,0.06),transparent)]">
        <div className="mx-auto w-full max-w-[1500px] px-4 py-16 md:px-8 lg:py-20">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1fr)] lg:items-start">
            <div>
              <span className="mono-label text-foreground/40">For research teams</span>
              <h2 className="mt-3 text-balance font-display text-3xl leading-tight text-foreground sm:text-4xl">
                A study surface you can defend.
              </h2>
              <p className="mt-4 max-w-lg text-sm leading-7 text-foreground/55">
                Run local, keep participant data on your own machine, and hand a reviewer a session that
                includes its own version history and uncertainty boundary. The instrument is experimental;
                the provenance is real.
              </p>
              <div className="mt-6 flex flex-wrap gap-2.5">
                <Link
                  href="https://github.com/toniIepure25/Imagina/issues"
                  className="inline-flex min-h-11 items-center rounded-lg border border-white/15 px-4 text-sm font-semibold text-foreground/80 transition-colors hover:border-accent-glow/40 hover:text-foreground"
                >
                  Open a research inquiry
                </Link>
                <Link
                  href="/animus/about"
                  className="inline-flex min-h-11 items-center rounded-lg px-4 text-sm text-foreground/55 transition-colors hover:text-foreground"
                >
                  Capability envelope →
                </Link>
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                ["Local deployment", "SQLite, files, and backups stay under your control."],
                ["Versioned evidence", "Every scene change and export has a durable record."],
                ["Explicit status", "Simulation, pilot, blocked, and human evidence are kept separate."],
                ["No decoding lane", "No raw neural data and no external inference service."],
              ].map(([title, body]) => (
                <div key={title} className="rounded-lg border border-white/10 bg-white/[0.02] p-4">
                  <p className="text-sm font-medium text-foreground/85">{title}</p>
                  <p className="mt-2 text-xs leading-5 text-foreground/45">{body}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-10 rounded-lg border border-amber-300/15 bg-amber-300/[0.04] p-4 text-sm leading-6 text-foreground/60">
            <span className="font-medium text-amber-200/80">Evidence status.</span> No human CRT data has
            been collected. Stage 0I is simulation-only; target-scale NUTS/SBC remains blocked. CI green
            is process evidence, not scientific validation.
          </div>
        </div>
      </section>

      <div className="mx-auto w-full max-w-[1500px] px-4 pb-12 md:px-8">
        <BoundaryNote />
      </div>
    </AppShell>
  );
}
