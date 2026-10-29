"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { useFocusTrap } from "@/lib/useFocusTrap";
import { EVIDENCE_KIND_COPY, EVIDENCE_KIND_LABEL, EVIDENCE_KIND_LETTER } from "@/lib/evidence/types";
import { useGlassBox } from "./GlassBoxContext";

export default function EvidenceDrawer() {
  const { activeEntry, closeEvidence } = useGlassBox();
  const panelRef = useRef<HTMLElement | null>(null);
  const open = Boolean(activeEntry);
  useFocusTrap(open, panelRef);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeEvidence();
      }
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [closeEvidence, open]);

  if (!activeEntry) return null;

  return (
    <div className="fixed inset-0 z-[120] flex justify-end">
      <button
        type="button"
        aria-label="Dismiss evidence panel"
        className="absolute inset-0 bg-black/60 backdrop-blur-[2px]"
        onClick={closeEvidence}
      />
      <aside
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="evidence-drawer-title"
        tabIndex={-1}
        className="relative z-10 flex h-full w-full max-w-md flex-col border-l border-surface-border bg-background shadow-2xl outline-none sm:max-w-lg"
      >
        <header className="flex items-start justify-between gap-4 border-b border-surface-border p-5">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-6 w-6 items-center justify-center rounded border border-signal/30 bg-signal/10 font-mono text-[11px] text-signal">
                {EVIDENCE_KIND_LETTER[activeEntry.kind]}
              </span>
              <span className="mono-label text-foreground/45">{EVIDENCE_KIND_LABEL[activeEntry.kind]}</span>
            </div>
            <h2 id="evidence-drawer-title" className="mt-3 text-xl font-semibold tracking-tight">
              {activeEntry.label}
            </h2>
            <p className="mt-1 font-mono text-[11px] text-foreground/40">{activeEntry.id}</p>
          </div>
          <button
            type="button"
            onClick={closeEvidence}
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-surface-border text-foreground/60 hover:bg-white/[0.04] hover:text-foreground"
            aria-label="Close evidence panel"
          >
            ×
          </button>
        </header>

        <div className="flex-1 space-y-6 overflow-y-auto p-5">
          <section>
            <h3 className="mono-label text-foreground/40">What it is</h3>
            <p className="mt-2 text-sm leading-6 text-foreground/75">{activeEntry.what}</p>
          </section>

          <section>
            <h3 className="mono-label text-foreground/40">Source</h3>
            <p className="mt-2 break-words font-mono text-[12px] leading-5 text-signal/80">{activeEntry.source}</p>
          </section>

          <section>
            <h3 className="mono-label text-foreground/40">Method</h3>
            <p className="mt-2 text-sm leading-6 text-foreground/65">{activeEntry.method}</p>
          </section>

          <section>
            <h3 className="mono-label text-foreground/40">Uncertainty</h3>
            <p className="mt-2 text-sm leading-6 text-lock/80">{activeEntry.uncertainty}</p>
          </section>

          <section className="rounded-lg border border-danger/25 bg-danger/[0.045] p-4">
            <h3 className="mono-label text-danger/70">What it cannot show</h3>
            <p className="mt-2 text-sm leading-6 text-foreground/70">{activeEntry.cannot}</p>
          </section>

          <section>
            <h3 className="mono-label text-foreground/40">Surfaces</h3>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {activeEntry.surfaces.map((surface) => (
                <span
                  key={surface}
                  className="rounded border border-surface-border px-2 py-1 font-mono text-[11px] text-foreground/50"
                >
                  {surface}
                </span>
              ))}
            </div>
          </section>
        </div>

        <footer className="space-y-2 border-t border-surface-border p-5">
          {activeEntry.studyEligible ? (
            <Link
              href={`/research/design?from=${encodeURIComponent(activeEntry.id)}`}
              className="inline-flex min-h-11 w-full items-center justify-center rounded-lg border border-signal/30 bg-signal/[0.08] px-4 text-sm font-medium text-signal hover:bg-signal/[0.13]"
              onClick={closeEvidence}
            >
              Design a study from this claim
            </Link>
          ) : null}
          <Link
            href="/method"
            className="inline-flex min-h-11 w-full items-center justify-center rounded-lg border border-surface-border px-4 text-sm text-foreground/65 hover:bg-white/[0.04] hover:text-foreground"
            onClick={closeEvidence}
          >
            Open the Method &amp; Claim Atlas
          </Link>
          <p className="pt-1 text-[11px] leading-5 text-foreground/35">
            {EVIDENCE_KIND_COPY[activeEntry.kind]} Reviewed {activeEntry.reviewedAt}.
          </p>
        </footer>
      </aside>
    </div>
  );
}
