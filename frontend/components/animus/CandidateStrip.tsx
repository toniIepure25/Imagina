"use client";

import Button from "@/components/common/Button";
import type { StudioCandidate } from "@/lib/animusStudioApi";
import SceneSketch from "./SceneSketch";
import { entityKindLabel } from "./sceneUtils";

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
  currentVersionId,
  previewCandidateId,
  busy,
  onPreview,
  onSelect,
  onRegenerate,
}: {
  candidates: StudioCandidate[];
  activeHash: string;
  currentVersionId: string;
  previewCandidateId: string | null;
  busy: boolean;
  onPreview: (candidate: StudioCandidate) => void;
  onSelect: (candidate: StudioCandidate) => Promise<unknown>;
  onRegenerate: () => Promise<unknown>;
}) {
  return (
    <section
      aria-label="Candidate variations"
      aria-busy={busy}
      className="border-t border-surface-border bg-[#080a0c]/95 px-3 py-2.5"
    >
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="flex items-baseline gap-2">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-signal/70">Candidate set</h2>
          <span className="text-[11px] text-foreground/30" role="status" aria-live="polite">
            {busy
              ? "generating controlled variations…"
              : candidates.length
                ? "preview freely · keep only what fits"
                : "explore controlled variations"}
          </span>
        </div>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => void onRegenerate()}
          disabled={busy}
          className="text-[11px]"
        >
          {busy ? "Working…" : candidates.length ? "Explore again" : "Explore 3 variations"}
        </Button>
      </div>
      {candidates.length === 0 ? (
        <div className="flex items-center gap-3 rounded-lg border border-dashed border-white/10 bg-white/[0.015] px-3 py-2.5">
          <div className="h-8 w-8 rounded-full border border-signal/25 bg-signal/10" aria-hidden="true" />
          <p className="text-[11px] leading-relaxed text-foreground/40">
            {busy
              ? "Building deterministic variations that preserve locked elements and explicit edits."
              : "Variations preserve your locks and explicit edits. Preview one, then keep it to create a new version; nothing is overwritten."}
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
            const previewing = candidate.candidate_id === previewCandidateId;
            const stale = candidate.source_version_id !== currentVersionId;
            const subject = candidate.scene.entities.find((entity) => entity.role === "subject");
            const label = String.fromCharCode(65 + index);
            return (
              <article
                key={candidate.candidate_id}
                role="listitem"
                aria-current={previewing || selected ? "true" : undefined}
                data-testid="candidate-card"
                className={`group min-w-[206px] max-w-[232px] flex-1 overflow-hidden rounded-lg border transition-colors ${
                  previewing
                    ? "border-lock/55 bg-lock/[0.05]"
                    : selected
                      ? "border-signal/45 bg-signal/[0.03]"
                      : "border-white/10 bg-white/[0.02] hover:border-white/25"
                }`}
              >
                <div className="relative h-16 overflow-hidden" aria-hidden="true">
                  <SceneSketch scene={candidate.scene} className="h-full w-full" />
                  <span className="absolute left-2 top-1.5 rounded bg-black/45 px-1.5 py-0.5 font-mono text-[11px] text-white/85">
                    {label}
                  </span>
                  {previewing ? (
                    <span className="absolute right-2 top-1.5 rounded-full bg-lock px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-black">
                      preview
                    </span>
                  ) : selected ? (
                    <span className="absolute right-2 top-1.5 rounded-full bg-signal px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-black">
                      active
                    </span>
                  ) : null}
                  <div className="absolute bottom-1.5 left-2 right-2 truncate text-[11px] font-medium text-white/85">
                    {subject?.label || candidate.scene.title}
                  </div>
                </div>
                <div className="space-y-1.5 p-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-[11px] text-foreground/55">
                      {subject ? entityKindLabel(subject.kind) : "scene"} · {candidate.scene.entities.length} el.
                    </span>
                    <span className="shrink-0 font-mono text-[11px] text-foreground/30">
                      {candidate.scene.metadata.content_hash?.slice(0, 6)}
                    </span>
                  </div>
                  <p className="truncate text-[11px] text-foreground/45" title={candidate.notes.join(" · ")}>
                    {candidate.notes[0] ?? diffLine(candidate)}
                  </p>
                  <p className="truncate font-mono text-[11px] text-foreground/25">{diffLine(candidate)}</p>
                  {stale ? (
                    <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-lock/70">stale · head changed</p>
                  ) : null}
                  <div className="flex gap-1.5">
                    <button
                      type="button"
                      onClick={() => onPreview(candidate)}
                      aria-pressed={previewing}
                      aria-label={previewing ? `Stop previewing candidate ${label}` : `Preview candidate ${label}`}
                      className={`flex-1 rounded-md border px-1.5 py-1 text-[11px] transition-colors ${
                        previewing
                          ? "border-lock/45 text-lock"
                          : "border-white/12 text-foreground/55 hover:border-lock/35 hover:text-lock"
                      }`}
                    >
                      {previewing ? "Previewing" : "Preview"}
                    </button>
                    <button
                      type="button"
                      disabled={busy || selected || stale}
                      onClick={() => void onSelect(candidate)}
                      aria-label={selected ? `Candidate ${label} is active` : `Keep candidate ${label}`}
                      className={`flex-1 rounded-md border px-1.5 py-1 text-[11px] font-medium transition-colors disabled:cursor-default disabled:opacity-35 ${
                        selected ? "border-signal/25 text-signal/60" : "border-white/12 text-foreground/65 hover:border-signal/40"
                      }`}
                    >
                      {selected ? "In studio" : "Keep"}
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
