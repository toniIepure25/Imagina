"use client";

import type { EvidenceItem } from "@/lib/animusStudioApi";

export default function EvidenceTrail({ items }: { items: EvidenceItem[] }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-medium">Evidence trail</h2>
        <span className="text-[11px] text-foreground/35">
          {items.reduce((total, item) => total + item.n_sources, 0)} source recordings
        </span>
      </div>
      <p className="mt-1 text-xs leading-relaxed text-foreground/45">
        This records which model inputs support each feature. It is provenance, not a causal explanation
        of memory.
      </p>
      <div className="mt-4 space-y-2">
        {items.map((item) => (
          <details key={item.variable_id} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
            <summary className="cursor-pointer list-none">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-medium text-foreground/80">{item.label}</span>
                <span className="text-[11px] uppercase tracking-[0.14em] text-foreground/35">
                  {item.provenance.replace(/_/g, " ")} · {item.n_sources} source
                  {item.n_sources === 1 ? "" : "s"}
                </span>
              </div>
            </summary>
            <div className="mt-3 space-y-2">
              {item.sources.length === 0 ? (
                <p className="text-[11px] text-foreground/40">
                  No direct probe; this feature remains at the prior.
                </p>
              ) : (
                item.sources.map((source, sourceIndex) => (
                  <div
                    key={`${source.probe_id}:${sourceIndex}`}
                    className="rounded-lg border border-white/5 bg-black/10 px-3 py-2 text-[11px] text-foreground/50"
                  >
                    <div className="flex flex-wrap justify-between gap-2">
                      <span>{source.probe_type.replace(/_/g, " ")}</span>
                      <span className="tabular-nums">
                        {source.abstained ? "abstained" : `confidence ${Math.round((source.confidence ?? 0) * 100)}%`}
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap justify-between gap-2 text-foreground/35">
                      <span>{source.probe_id}</span>
                      <span>
                        gain{" "}
                        {typeof source.information_gain === "number"
                          ? source.information_gain.toFixed(3)
                          : "—"}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </details>
        ))}
        {items.length === 0 ? (
          <p className="text-xs text-foreground/40">No epistemic evidence is available yet.</p>
        ) : null}
      </div>
    </section>
  );
}
