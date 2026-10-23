"use client";

import Button from "@/components/common/Button";
import type { StudioCandidate } from "@/lib/animusStudioApi";
import { entityKindLabel, sceneGradient } from "./sceneUtils";

function diffLine(candidate: StudioCandidate): string {
  const { added, changed, removed, locked_untouched } = candidate.diff;
  const parts: string[] = [];
  if (added.length) parts.push(`+${added.length}`);
  if (changed.length) parts.push(`~${changed.length}`);
  if (removed.length) parts.push(`−${removed.length}`);
  if (locked_untouched.length) parts.push(`${locked_untouched.length} kept`);
  return parts.join(" · ") || "subtle variation";
}

export default function CandidateStrip({
  candidates,
  activeHash,
  busy,
  onSelect,
  onRegenerate,
}: {
  candidates: StudioCandidate[];
  activeHash: string;
  busy: boolean;
  onSelect: (candidate: StudioCandidate) => Promise<unknown>;
  onRegenerate: () => Promise<unknown>;
}) {
  return (
    <section
      aria-label="Candidate variations"
      aria-busy={busy}
      className="border-t border-surface-border bg-[#080a12]/90 px-4 py-3"
    >
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="flex items-baseline gap-2">
          <h2 className="text-[10px] uppercase tracking-[0.22em] text-accent-glow/70">Candidate set</h2>
          <span className="text-[10px] text-foreground/30" role="status" aria-live="polite">
            {busy
              ? "generating controlled variations…"
              : candidates.length
                ? "pick one to keep, or explore again"
                : "explore controlled variations"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => void onRegenerate()}
            disabled={busy}
            className="text-[11px]"
            aria-label="Generate new candidate variations"
          >
            {busy ? "Working…" : candidates.length ? "Explore again" : "Explore 3 variations"}
          </Button>
        </div>
      </div>
      {candidates.length === 0 ? (
        <div className="flex items-center gap-3 rounded-lg border border-dashed border-white/10 bg-white/[0.015] px-3 py-2.5">
          <div className="h-8 w-8 rounded-full border border-accent-glow/25 bg-accent-glow/10" aria-hidden="true" />
          <p className="text-[11px] leading-relaxed text-foreground/40">
            {busy
              ? "Building deterministic variations that preserve locked elements and explicit edits."
              : "Variations preserve your locked elements and explicit edits. Select one to create a new version; nothing is overwritten."}
          </p>
        </div>
      ) : (
        <div
          role="list"
          aria-label="Candidate variations"
          className="flex gap-2 overflow-x-auto pb-1 [scrollbar-width:thin]"
        >
          {candidates.map((candidate, index) => {
            const selected = candidate.scene.metadata.content_hash === activeHash;
            const subject = candidate.scene.entities.find((entity) => entity.role === "subject");
            const label = String.fromCharCode(65 + index);
            return (
              <article
                key={candidate.candidate_id}
                role="listitem"
                aria-current={selected ? "true" : undefined}
                data-testid="candidate-card"
                className={`group min-w-[196px] max-w-[220px] flex-1 overflow-hidden rounded-lg border transition-colors ${
                  selected
                    ? "border-accent-glow/50 bg-accent-glow/[0.04]"
                    : "border-white/10 bg-white/[0.02] hover:border-white/25"
                }`}
              >
                <div
                  className="relative h-16 overflow-hidden"
                  style={{ background: sceneGradient(candidate.scene) }}
                  aria-hidden="true"
                >
                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_25%,rgba(255,255,255,0.22),transparent_45%)]" />
                  <span className="absolute left-2 top-1.5 rounded bg-black/35 px-1.5 py-0.5 font-mono text-[9px] text-white/80">
                    {label}
                  </span>
                  {selected && (
                    <span className="absolute right-2 top-1.5 rounded-full bg-accent-glow px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wide text-black">
                      active
                    </span>
                  )}
                  <div className="absolute bottom-1.5 left-2 right-2 truncate text-[10px] font-medium text-white/85">
                    {subject?.label || candidate.scene.title}
                  </div>
                </div>
                <div className="space-y-1.5 p-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-[10px] text-foreground/55">
                      {subject ? entityKindLabel(subject.kind) : "scene"} · {candidate.scene.entities.length} el.
                    </span>
                    <span className="shrink-0 font-mono text-[9px] text-foreground/30">
                      {candidate.scene.metadata.content_hash?.slice(0, 6)}
                    </span>
                  </div>
                  <p className="truncate text-[10px] text-foreground/35" title={candidate.notes.join(" · ")}>
                    {diffLine(candidate)}
                  </p>
                  <button
                    type="button"
                    disabled={busy || selected}
                    onClick={() => void onSelect(candidate)}
                    aria-label={selected ? `Candidate ${label} is active` : `Keep candidate ${label}`}
                    className={`w-full rounded-md border px-2 py-1 text-[10px] font-medium transition-colors disabled:cursor-default ${
                      selected
                        ? "border-accent-glow/25 text-accent-glow/60"
                        : "border-white/12 text-foreground/65 hover:border-accent-glow/40 hover:text-foreground"
                    }`}
                  >
                    {selected ? "In the studio" : "Keep this"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
