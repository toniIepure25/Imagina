"use client";

import { useEffect, useRef } from "react";
import Button from "@/components/common/Button";
import { useFocusTrap } from "@/lib/useFocusTrap";

export default function ConsentDialog({
  open,
  prompt,
  vectorHash,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  prompt: string;
  vectorHash: string;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  useFocusTrap(open, panelRef);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onCancel, open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCancel();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="consent-title"
        tabIndex={-1}
        className="w-full max-w-lg rounded-2xl border border-signal/25 bg-[#080b14] p-5 shadow-2xl sm:p-6"
      >
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-signal/70">Remote diffusion consent</p>
        <h2 id="consent-title" className="mt-2 font-display text-xl text-foreground">
          Send this request to the A100 worker?
        </h2>
        <p className="mt-2 text-sm leading-6 text-foreground/55">
          The worker is not attached in this demo. This dialog describes the exact payload that a configured worker
          would receive.
        </p>

        <dl className="mt-4 space-y-2 rounded-xl border border-white/10 bg-white/[0.025] p-3 text-xs">
          <div className="flex justify-between gap-4">
            <dt className="text-foreground/40">Prompt</dt>
            <dd className="max-w-[70%] truncate text-right text-foreground/70">{prompt}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-foreground/40">Conditioning</dt>
            <dd className="font-mono text-signal/80">16 derived values · {vectorHash}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-foreground/40">Never sent</dt>
            <dd className="text-right text-foreground/70">raw EEG · HRV · EDA · session id</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-foreground/40">Retention</dt>
            <dd className="text-right text-foreground/70">local job 24 h · worker assets 1 h</dd>
          </div>
        </dl>

        <p className="mt-3 text-[11px] leading-5 text-foreground/35">
          Output is a generated environment texture. It is an aesthetic aid, not a reconstruction, a measurement, or a
          validated imagery score.
        </p>

        <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="ghost" size="sm" onClick={onCancel} className="min-h-11">
            Keep local
          </Button>
          <Button variant="primary" size="sm" onClick={onConfirm} className="min-h-11">
            I consent · request skybox
          </Button>
        </div>
      </div>
    </div>
  );
}
