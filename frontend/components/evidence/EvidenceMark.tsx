"use client";

import { getEvidence } from "@/lib/evidence/registry";
import { EVIDENCE_KIND_LABEL, EVIDENCE_KIND_LETTER, type EvidenceKind } from "@/lib/evidence/types";
import { useGlassBox } from "./GlassBoxContext";

const KIND_STYLES: Record<EvidenceKind, string> = {
  measured: "border-signal/35 bg-signal/[0.08] text-signal hover:bg-signal/[0.15]",
  derived: "border-lock/35 bg-lock/[0.08] text-lock hover:bg-lock/[0.15]",
  simulated: "border-accent/35 bg-accent/[0.1] text-accent-glow hover:bg-accent/[0.18]",
  narrative: "border-surface-border bg-white/[0.035] text-foreground/55 hover:bg-white/[0.07]",
};

export default function EvidenceMark({
  evidenceId,
  className = "",
}: {
  evidenceId: string;
  className?: string;
}) {
  const { enabled, openEvidence } = useGlassBox();
  const entry = getEvidence(evidenceId);
  if (!entry) {
    return (
      <span
        className={`inline-flex h-6 w-6 items-center justify-center rounded border border-danger/40 bg-danger/[0.08] font-mono text-[11px] text-danger ${className}`}
        title={`Unregistered evidence id: ${evidenceId}`}
      >
        ?
      </span>
    );
  }
  if (!enabled) return null;

  return (
    <button
      type="button"
      onClick={() => openEvidence(entry.id)}
      className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded border font-mono text-[11px] leading-none transition-colors ${KIND_STYLES[entry.kind]} ${className}`}
      aria-label={`Evidence: ${entry.label}. ${EVIDENCE_KIND_LABEL[entry.kind]}. Open provenance.`}
      title={`${entry.label} · ${EVIDENCE_KIND_LABEL[entry.kind]}`}
    >
      {EVIDENCE_KIND_LETTER[entry.kind]}
    </button>
  );
}
