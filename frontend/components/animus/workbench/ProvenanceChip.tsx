"use client";

import { provenanceLabel } from "@/lib/sceneContract";

const TONE: Record<string, string> = {
  user_explicit: "border-signal/40 text-signal/85",
  user_implied: "border-signal/25 text-signal/70",
  candidate: "border-lock/35 text-lock/80",
  seed: "border-white/12 text-foreground/45",
  procedural: "border-white/12 text-foreground/45",
};

export default function ProvenanceChip({
  provenance,
  locked = false,
  className = "",
}: {
  provenance: string | null | undefined;
  locked?: boolean;
  className?: string;
}) {
  const key = provenance ?? "";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 font-mono text-[11px] uppercase tracking-[0.12em] ${
        TONE[key] ?? "border-white/12 text-foreground/40"
      } ${className}`}
      title={`Scene-graph source: ${provenanceLabel(provenance)}. This describes where the value came from, not why it was imagined.`}
    >
      <span aria-hidden="true" className="h-1 w-1 rounded-full bg-current" />
      {provenanceLabel(provenance)}
      {locked ? <span className="text-lock">· lock</span> : null}
    </span>
  );
}
