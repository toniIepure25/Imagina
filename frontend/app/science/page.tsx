import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import PageHeader from "@/components/platform/PageHeader";
import ClaimBadge from "@/components/platform/ClaimBadge";
import BoundaryNote from "@/components/platform/BoundaryNote";
import EvidenceMark from "@/components/evidence/EvidenceMark";
import EvidenceRail from "@/components/evidence/EvidenceRail";
import { CLAIM_CEILING, MEASUREMENT_BOUNDARY, PLATFORM_BOUNDARY } from "@/lib/claims";

const METRICS = [
  {
    name: "IQI",
    evidenceId: "iqi.proxy",
    full: "Imagery Quality Index",
    direction: "Higher is treated as a stronger proxy.",
    definition:
      "Weighted combination of attention stability, imagery engagement, behavioral consistency, relaxation, and confidence.",
    caution: "The weights are design choices, not psychometric loadings. Do not read IQI as an imagery score.",
  },
  {
    name: "PID",
    evidenceId: "pid.proxy",
    full: "Perception–Imagination Distance",
    direction: "Lower is treated as closer alignment.",
    definition:
      "Distance-like proxy from simulated neural features, behavioral distance, and uncertainty.",
    caution: "The neural term is simulated in this build. PID is not a measurement of actual cortical distance.",
  },
  {
    name: "Attention stability",
    evidenceId: "attention.proxy",
    full: "Theta/beta-style proxy",
    direction: "Higher is more stable.",
    definition:
      "Inverse of a theta/beta-style ratio, blended with self-report attention when available.",
    caution: "Derived from simulated or imported features; not a diagnostic EEG marker.",
  },
  {
    name: "Fatigue",
    evidenceId: "fatigue.proxy",
    full: "Trend-based load proxy",
    direction: "Higher is more fatigued.",
    definition:
      "Trend in theta and lower-alpha activity, self-report fatigue, and elapsed session time.",
    caution: "Used for safety overrides, not for clinical assessment.",
  },
];

const EVIDENCE = [
  {
    claim: "The closed loop runs end to end on this machine.",
    status: "Demonstrated",
    basis: "Deterministic replay, persisted event log, reproducible reports.",
    next: "Independent rerun from a clean environment.",
  },
  {
    claim: "The scene adapts to an estimated state.",
    status: "Demonstrated in simulation",
    basis: "Feedback policy maps proxy state to ten procedural parameters.",
    next: "Test whether adaptation improves a pre-registered behavioral outcome.",
  },
  {
    claim: "Text and a signal vector compose a walkable layered world.",
    status: "Demonstrated locally",
    basis: "Deterministic Lumen world grammar, layered composer, first-person collision, and explicit provenance.",
    next: "Evaluate spatial coherence and preference without claiming imagery reconstruction.",
  },
  {
    claim: "The proxy metrics track imagery quality.",
    status: "Not established",
    basis: "No human-subjects validation in this repository.",
    next: "Powered study with convergent and discriminant measures.",
  },
  {
    claim: "The system can decode or reconstruct mental imagery.",
    status: "Rejected by design",
    basis: "No image model, no raw neural decoding, no mental-content output.",
    next: "Not a research goal; would require a different ethical and technical program.",
  },
];

const LIMITS = [
  "This build can use simulated EEG-like signals; simulated signals cannot validate a neural claim.",
  "Self-report is subjective and may reflect demand characteristics or response bias.",
  "PID and IQI are experimental composites whose weights and ranges still need validation.",
  "The corridor is feedback scaffolding, not a reconstruction of mental content.",
  "The Lumen world is a procedural interpretation of a written brief, not a generated image of what a person imagined.",
  "No clinical evaluation, diagnosis, or treatment claim is supported.",
  "Small local sessions cannot establish population-level effects.",
];

const ROADMAP = [
  ["Now", "Deterministic replay, event provenance, safety monitor, local export."],
  ["Next", "Artifact-aware import, channel checks, and a pre-registered analysis plan."],
  ["Later", "Independent replication with convergent measures and reported effect sizes."],
  ["Only then", "Any claim stronger than L1 behavioral assistance."],
];

export default function SciencePage() {
  return (
    <AppShell level={1}>
      <div className="mx-auto w-full max-w-6xl space-y-6 px-4 py-8 md:px-6 lg:py-10">
        <PageHeader
          eyebrow="Scientific framing"
          title="What this instrument can and cannot support"
          description="IMAGINA is a local-first closed-loop prototype. It estimates experimental proxy metrics from self-report, behavior, and simulated signals, then adapts a procedural corridor as feedback. Lumen extends the same boundary into a walkable, layered world. The scene is a scaffold, not a decoded mental image."
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <ClaimBadge />
              <Link
                href="/method"
                className="inline-flex h-11 items-center rounded-lg border border-surface-border px-3 text-[11px] text-foreground/60 hover:bg-white/[0.04] hover:text-foreground"
              >
                Method &amp; claims
              </Link>
            </div>
          }
          meta={
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-foreground/35">
              claim ceiling · {CLAIM_CEILING}
            </span>
          }
        />

        <section className="grid gap-3 md:grid-cols-3">
          {[
            ["Claim ceiling", "L1 · behavioral assisted", "No neural decoding, diagnosis, or clinical benefit is claimed."],
            ["Validation state", "Prototype", "No human-subjects validation is bundled with this build."],
            ["Data boundary", "Local only", "No telemetry, no cloud accounts, no raw neural data leaves the machine."],
          ].map(([label, value, detail]) => (
            <div key={label} className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
              <p className="mono-label text-foreground/40">{label}</p>
              <p className="mt-2 text-lg font-medium text-foreground/85">{value}</p>
              <p className="mt-1 text-xs leading-5 text-foreground/45">{detail}</p>
            </div>
          ))}
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.025] p-5" aria-labelledby="metrics-title">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <p className="mono-label text-accent-glow/65">Metric definitions</p>
              <h2 id="metrics-title" className="mt-1 text-2xl font-semibold tracking-tight text-foreground">
                Proxies, not measurements
              </h2>
            </div>
            <p className="max-w-md text-xs leading-5 text-foreground/45">{MEASUREMENT_BOUNDARY}</p>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {METRICS.map((metric) => (
              <article key={metric.name} className="rounded-lg border border-white/8 bg-black/15 p-4">
                <div className="flex items-baseline justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-mono text-sm text-accent-glow/85">{metric.name}</h3>
                    <EvidenceMark evidenceId={metric.evidenceId} />
                  </div>
                  <span className="text-[11px] text-foreground/35">{metric.full}</span>
                </div>
                <p className="mt-2 text-xs leading-5 text-foreground/60">{metric.definition}</p>
                <p className="mt-2 text-xs leading-5 text-foreground/45">{metric.direction}</p>
                <p className="mt-2 border-t border-white/8 pt-2 text-[11px] leading-5 text-lock/70">{metric.caution}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.025] p-5" aria-labelledby="evidence-title">
          <p className="mono-label text-accent-glow/65">Evidence ladder</p>
          <h2 id="evidence-title" className="mt-1 text-2xl font-semibold tracking-tight text-foreground">
            What each claim rests on
          </h2>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[720px] border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-white/10 font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/40">
                  <th className="py-2 pr-4 font-normal">Claim</th>
                  <th className="py-2 pr-4 font-normal">Status</th>
                  <th className="py-2 pr-4 font-normal">Basis in this build</th>
                  <th className="py-2 font-normal">What would change it</th>
                </tr>
              </thead>
              <tbody>
                {EVIDENCE.map((row) => (
                  <tr key={row.claim} className="border-b border-white/[0.07] last:border-0">
                    <td className="py-3 pr-4 align-top text-foreground/75">{row.claim}</td>
                    <td className="py-3 pr-4 align-top">
                      <span
                        className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] ${
                          row.status.startsWith("Demonstrated")
                            ? "border-signal/25 bg-signal/[0.06] text-signal/85"
                            : row.status === "Not established"
                              ? "border-lock/25 bg-lock/[0.06] text-lock/85"
                              : "border-danger/25 bg-danger/[0.06] text-danger/80"
                        }`}
                      >
                        {row.status}
                      </span>
                    </td>
                    <td className="py-3 pr-4 align-top leading-5 text-foreground/50">{row.basis}</td>
                    <td className="py-3 align-top leading-5 text-foreground/50">{row.next}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <div className="grid gap-4 lg:grid-cols-2">
          <section className="rounded-xl border border-lock/20 bg-lock/[0.04] p-5">
            <p className="mono-label text-lock/70">Limitations</p>
            <h2 className="mt-1 text-xl font-semibold text-foreground">Known limits of this build</h2>
            <ul className="mt-3 space-y-2 text-xs leading-5 text-foreground/60">
              {LIMITS.map((limit) => (
                <li key={limit} className="flex gap-2">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-lock" aria-hidden="true" />
                  {limit}
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-xl border border-white/10 bg-white/[0.025] p-5">
            <p className="mono-label text-foreground/45">Validation path</p>
            <h2 className="mt-1 text-xl font-semibold text-foreground">From demo to evidence</h2>
            <ol className="mt-3 space-y-2.5">
              {ROADMAP.map(([phase, detail], index) => (
                <li key={phase} className="flex gap-3">
                  <span className="mt-0.5 font-mono text-[11px] text-accent-glow/55">{String(index + 1).padStart(2, "0")}</span>
                  <div>
                    <p className="text-xs font-medium text-foreground/75">{phase}</p>
                    <p className="text-[11px] leading-5 text-foreground/45">{detail}</p>
                  </div>
                </li>
              ))}
            </ol>
            <Link href="/research" className="mt-4 inline-flex min-h-9 items-center text-xs text-accent-glow/80 hover:text-accent-glow">
              Open the research console →
            </Link>
          </section>
        </div>

        <EvidenceRail />
        <BoundaryNote>{PLATFORM_BOUNDARY}</BoundaryNote>
      </div>
    </AppShell>
  );
}
