"use client";

import type { ObservatoryReliability } from "@/lib/animusStudioApi";

function number(value: number | null | undefined, digits = 3): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—";
}

export default function ReliabilityPanel({ reliability }: { reliability: ObservatoryReliability }) {
  const estimated = reliability.status === "estimated";
  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-medium">Test–retest consistency</h2>
        <span className="text-[11px] text-foreground/35">
          {reliability.n_occasions} occasion{reliability.n_occasions === 1 ? "" : "s"}
        </span>
      </div>
      {estimated ? (
        <>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <p className="text-[11px] uppercase tracking-[0.18em] text-foreground/35">r</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums">{number(reliability.r)}</p>
              <p className="mt-1 text-[11px] text-foreground/40">
                {reliability.r_ci ? `95% CI ${number(reliability.r_ci[0])} to ${number(reliability.r_ci[1])}` : "no interval"}
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.18em] text-foreground/35">SEM</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums">{number(reliability.sem)}</p>
              <p className="mt-1 text-[11px] text-foreground/40">measurement error</p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.18em] text-foreground/35">MDC95</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums">{number(reliability.mdc95)}</p>
              <p className="mt-1 text-[11px] text-foreground/40">minimal detectable change</p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.18em] text-foreground/35">Δ d′</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums">
                {number(reliability.dprime_change)}
              </p>
              <p className="mt-1 text-[11px] text-foreground/40">later minus earlier</p>
            </div>
          </div>
          <p className="mt-4 text-[11px] leading-relaxed text-foreground/40">
            r is reported only when at least three aligned feature estimates exist. A change smaller than
            MDC95 is not distinguishable from measurement error in this sample.
          </p>
        </>
      ) : (
        <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.02] p-4">
          <p className="text-sm text-foreground/60">
            {reliability.reason || "Not enough repeated evidence yet."}
          </p>
          <p className="mt-1 text-xs leading-relaxed text-foreground/40">
            Complete a second contrast session on the same scene, ideally after a delay, to estimate
            consistency. No normative comparison is produced.
          </p>
        </div>
      )}
      <p className="mt-4 text-[11px] text-foreground/35">
        Descriptive reliability, not a fixed trait; practice, fatigue, device, and strategy can change it.
      </p>
    </section>
  );
}
