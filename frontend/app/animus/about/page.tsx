import Link from "next/link";
import type { Metadata } from "next";
import AnimusShell from "@/components/animus/AnimusShell";

export const metadata: Metadata = {
  title: "About ANIMUS — boundaries, loop, and claims",
  description:
    "What ANIMUS does, what it deliberately does not do, and why every scene stays symbolic and local.",
};

const CAPABILITIES = [
  ["Symbolic scene graph", "ACTIVE", "ANIMUS-SG-v1; editable entities, attributes, relations, constraints"],
  ["Procedural renderer", "ACTIVE", "Local React Three Fiber preview; deterministic from the scene graph"],
  ["Candidate regeneration", "ACTIVE", "Seeded perturbations that preserve locks and explicit edits"],
  ["Image generation", "DISABLED", "No image model, diffusion pipeline, or external render service"],
  ["Neural content", "UNAUTHORIZED", "No inference of imagery or dream content from brain signals"],
  ["Dream content", "UNAUTHORIZED", "No dream decoding, neural reconstruction, or interpretation"],
  ["Neural reconstruction", "UNAUTHORIZED", "No neural reconstruction claim; behavioural reconstruction is separate"],
  ["Behavioural profile", "EXPERIMENTAL", "Five separate estimates with explicit evidence counts; no composite score"],
  ["Epistemic interview", "EXPERIMENTAL", "Binary probes, Beta posteriors, calibration, coverage, and abstention reported separately"],
  ["Scene Threshold", "EXPERIMENTAL", "Two-alternative contrast discrimination, adaptive staircase, SDT sensitivity, threshold, and test–retest reliability"],
  ["Clinical use", "DISABLED", "Not a diagnosis, treatment, or validated clinical instrument"],
  ["Network calls during studio use", "DISABLED", "The studio reads and writes only the local backend"],
  ["Uploads", "DISABLED", "No image, audio, or neural-data upload path"],
  ["Privacy scope", "LOCAL ONLY", "SQLite on this machine; no accounts, telemetry, or cloud sync"],
];

const LOOP = [
  ["Intention", "A natural-language description is parsed into typed, validated scene state."],
  ["Candidate", "A deterministic procedural renderer makes the state visible. One concrete scene, not a promise."],
  ["Correction", "You change a color, a style, an element, or a relationship. Each edit is a versioned command."],
  ["Convergence", "Lock what is right. Regeneration varies only what remains free, and reports what it preserved."],
  ["Keep or explore", "Select a candidate, undo, branch, save a world, or reopen it later from SQLite."],
];

export default function AnimusAboutPage() {
  return (
    <AnimusShell active="about">
      <div className="mx-auto w-full max-w-5xl px-6 py-12">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.22em] text-accent-glow/60">Scientific boundaries</div>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">What ANIMUS is — and is not</h1>
          </div>
          <Link href="/animus" className="text-[11px] text-foreground/45 hover:text-foreground">
            ← Back to Animus
          </Link>
        </div>

        <div className="mt-6 grid gap-3 md:grid-cols-2">
          <section className="rounded-xl border border-emerald-400/20 bg-emerald-400/[0.04] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-200/80">It is</h2>
            <ul className="mt-3 space-y-2 text-[11px] leading-relaxed text-foreground/55">
              <li>A behavioural scaffold for deliberate imagination practice.</li>
              <li>A closed loop of intention, visible candidate, correction, and convergence.</li>
              <li>A versioned, inspectable scene graph with deterministic rendering and regeneration.</li>
              <li>A local-first product: your scenes stay in SQLite on this machine.</li>
              <li>An experimental behavioural profile with object/spatial reconstruction, explicit evidence counts, and no composite score.</li>
              <li>An epistemic interview that reports posterior uncertainty, calibration, coverage, and abstention separately.</li>
              <li>A contrastive Scene Threshold task that estimates discrimination sensitivity and a within-scene threshold, not imagery strength.</li>
            </ul>
          </section>
          <section className="rounded-xl border border-amber-400/20 bg-amber-400/[0.04] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-200/80">It is not</h2>
            <ul className="mt-3 space-y-2 text-[11px] leading-relaxed text-foreground/55">
              <li>Not a mind reader, dream decoder, or neural reconstruction system.</li>
              <li>Not a clinical treatment, diagnostic tool, or validated neurofeedback device.</li>
              <li>Not an image generator: every candidate is a symbolic, procedural preview.</li>
              <li>Not evidence that imagery training generalises beyond this task.</li>
              <li>Not a validated psychometric or clinical instrument, and not a measure of imagery strength.</li>
            </ul>
          </section>
        </div>

        <section className="mt-10">
          <h2 className="text-lg font-semibold tracking-tight">The loop</h2>
          <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
            {LOOP.map(([title, body], index) => (
              <div key={title} className="rounded-lg border border-white/8 bg-white/[0.02] p-3">
                <div className="font-mono text-[11px] text-accent-glow/45">0{index + 1}</div>
                <h3 className="mt-1.5 text-xs font-medium text-foreground/80">{title}</h3>
                <p className="mt-1 text-[11px] leading-relaxed text-foreground/35">{body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-10">
          <div className="flex items-end justify-between gap-3">
            <h2 className="text-lg font-semibold tracking-tight">Capability envelope</h2>
            <span className="rounded-full border border-accent-glow/25 bg-accent-glow/5 px-2.5 py-1 text-[11px] uppercase tracking-[0.16em] text-accent-glow/70">
              claim ceiling L1 · behavioural-assisted
            </span>
          </div>
          <p className="mt-2 max-w-2xl text-[11px] leading-relaxed text-foreground/40">
            These values are enforced by the backend and returned with every studio session. The UI cannot raise
            them, and no endpoint exposes a path to enable neural or image-model content.
          </p>
          <div className="mt-4 overflow-hidden rounded-xl border border-white/10">
            <table className="w-full text-left text-[11px]">
              <thead className="bg-white/[0.03] text-[11px] uppercase tracking-[0.14em] text-foreground/35">
                <tr>
                  <th className="px-3 py-2 font-medium">Capability</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="hidden px-3 py-2 font-medium sm:table-cell">Boundary</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/6">
                {CAPABILITIES.map(([name, status, detail]) => (
                  <tr key={name} className="align-top">
                    <td className="px-3 py-2 text-foreground/65">{name}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded px-1.5 py-0.5 font-mono text-[11px] ${
                          status === "ACTIVE"
                            ? "bg-emerald-400/10 text-emerald-200/80"
                            : status === "DISABLED" || status === "LOCAL ONLY"
                              ? "bg-accent-glow/10 text-accent-glow/70"
                              : "bg-amber-400/10 text-amber-200/80"
                        }`}
                      >
                        {status}
                      </span>
                    </td>
                    <td className="hidden px-3 py-2 text-foreground/35 sm:table-cell">{detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-10 grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-white/8 bg-white/[0.02] p-4">
            <h2 className="text-sm font-semibold text-foreground/80">Why symbolic, not photoreal</h2>
            <p className="mt-2 text-[11px] leading-relaxed text-foreground/45">
              A photoreal image would hide the reasoning behind a candidate. A symbolic scene graph exposes every
              entity, attribute, provenance, and lock, so a correction is precise and a regenerated candidate can
              be diffed against what you just saw. It also keeps the product honest: no model is pretending to
              reconstruct an inner image.
            </p>
          </div>
          <div className="rounded-xl border border-white/8 bg-white/[0.02] p-4">
            <h2 className="text-sm font-semibold text-foreground/80">Why the claim ceiling is L1</h2>
            <p className="mt-2 text-[11px] leading-relaxed text-foreground/45">
              The loop is a behavioural interaction: you describe, inspect, correct, and keep a scene. No neural
              measurement is used, no imagery content is inferred, and no clinical outcome is claimed. Existing
              perception-decoding research elsewhere in the repository is not imagery validation and does not
              raise this ceiling.
            </p>
          </div>
          <div className="rounded-xl border border-white/8 bg-white/[0.02] p-4">
            <h2 className="text-sm font-semibold text-foreground/80">Local and auditable</h2>
            <p className="mt-2 text-[11px] leading-relaxed text-foreground/45">
              Sessions, versions, branches, candidates, and worlds are stored in local SQLite. Every version has a
              content hash. The studio makes no network calls beyond the local FastAPI backend, and there is no
              upload path, account, or telemetry.
            </p>
          </div>
          <div className="rounded-xl border border-white/8 bg-white/[0.02] p-4">
            <h2 className="text-sm font-semibold text-foreground/80">Known limitations</h2>
            <p className="mt-2 text-[11px] leading-relaxed text-foreground/45">
              The parser covers a bounded vocabulary; unknown nouns become abstract forms. The renderer is an
              approximation, not a physically accurate world. Benefits for imagery vividness or attention have
              not been established by a controlled study here. Do not use the studio as a medical or diagnostic
              tool.
            </p>
          </div>
        </section>

        <div className="mt-10 flex flex-wrap items-center gap-3 border-t border-white/8 pt-5">
          <Link
            href="/animus"
            className="rounded-lg bg-accent px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-glow hover:text-background"
          >
            Start a scene
          </Link>
          <Link href="/science" className="text-[11px] text-foreground/40 hover:text-foreground">
            Existing research notes →
          </Link>
        </div>
      </div>
    </AnimusShell>
  );
}
