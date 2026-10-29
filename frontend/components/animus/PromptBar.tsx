"use client";

import { useState, type FormEvent } from "react";
import Button from "@/components/common/Button";
import type { StudioSnapshot } from "@/lib/animusStudioApi";
import type { StudioNotice } from "@/lib/useAnimusStudio";

const EXAMPLES = [
  "make the sky deep violet",
  "make the castle gothic and keep the ocean",
  "add a second moon",
  "make it feel calmer",
  "add a glowing portal behind the castle",
];

const NOTICE_STYLES: Record<StudioNotice["kind"], string> = {
  info: "border-accent-glow/25 bg-accent-glow/10 text-accent-glow/90",
  success: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200/90",
  error: "border-danger/30 bg-danger/10 text-red-200/90",
};

interface IntentReceipt {
  text: string;
  applied: number;
  resolutions: string[];
  warnings: string[];
  needsClarification: boolean;
  clarification: string | null;
}

function receiptFrom(text: string, snapshot: StudioSnapshot | null): IntentReceipt {
  return {
    text,
    applied: snapshot?.applied ?? 0,
    resolutions: snapshot?.resolutions ?? [],
    warnings: snapshot?.parse_warnings ?? [],
    needsClarification: Boolean(snapshot?.needs_clarification),
    clarification: snapshot?.clarification ?? null,
  };
}

export default function PromptBar({
  busy,
  notice,
  onSubmit,
  onClearNotice,
  onOpenTrace,
}: {
  busy: boolean;
  notice: StudioNotice | null;
  onSubmit: (text: string) => Promise<StudioSnapshot | null>;
  onClearNotice: () => void;
  onOpenTrace?: () => void;
}) {
  const [text, setText] = useState("");
  const [receipt, setReceipt] = useState<IntentReceipt | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const value = text.trim();
    if (!value || busy) return;
    const result = await onSubmit(value);
    if (result !== undefined) {
      setReceipt(receiptFrom(value, result));
      setText("");
    }
  };

  return (
    <div className="border-t border-surface-border bg-background/80 px-4 py-3 backdrop-blur">
      {receipt ? (
        <section
          aria-label="Intent receipt"
          data-testid="intent-receipt"
          className="mb-2 rounded-lg border border-accent-glow/20 bg-accent-glow/[0.045] p-2.5"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent-glow/70">Intent receipt</p>
            <div className="flex items-center gap-2">
              <span
                className={`rounded-full border px-2 py-0.5 font-mono text-[11px] ${
                  receipt.needsClarification
                    ? "border-lock/30 bg-lock/10 text-lock/85"
                    : receipt.applied > 0
                      ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-200/85"
                      : "border-lock/30 bg-lock/10 text-lock/85"
                }`}
              >
                {receipt.needsClarification
                  ? "clarification"
                  : `${receipt.applied} command${receipt.applied === 1 ? "" : "s"} applied`}
              </span>
              {onOpenTrace ? (
                <button
                  type="button"
                  onClick={onOpenTrace}
                  className="min-h-7 rounded border border-white/12 px-2 text-[11px] text-foreground/55 hover:text-foreground"
                >
                  Open Trace
                </button>
              ) : null}
              <button
                type="button"
                onClick={() => setReceipt(null)}
                aria-label="Dismiss intent receipt"
                className="grid h-7 w-7 place-items-center rounded border border-white/10 text-xs text-foreground/35 hover:text-foreground"
              >
                ✕
              </button>
            </div>
          </div>
          <p className="mt-1.5 truncate text-xs text-foreground/65">“{receipt.text}”</p>
          {receipt.clarification ? (
            <p className="mt-1 text-xs leading-5 text-lock/85">{receipt.clarification}</p>
          ) : null}
          {receipt.resolutions.length ? (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {receipt.resolutions.slice(0, 4).map((item) => (
                <span key={item} className="rounded-full border border-white/10 bg-white/[0.03] px-2 py-0.5 text-[11px] text-foreground/50">
                  {item}
                </span>
              ))}
            </div>
          ) : null}
          {receipt.warnings.length ? (
            <p className="mt-1.5 text-[11px] leading-5 text-lock/80">
              {receipt.warnings.length} parser warning{receipt.warnings.length === 1 ? "" : "s"} ·{" "}
              {receipt.warnings[0]}
            </p>
          ) : null}
        </section>
      ) : null}

      <div className="mb-2 flex items-baseline justify-between gap-2">
        <p className="mono-label text-foreground/35">Intent lens</p>
        <p className="hidden text-[11px] text-foreground/30 sm:block">Text → typed commands, never an image model</p>
      </div>
      <div className="mb-2 flex gap-1.5 overflow-x-auto pb-1 [scrollbar-width:none]">
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            disabled={busy}
            onClick={() => setText(example)}
            className="min-h-7 shrink-0 rounded-full border border-white/10 bg-white/[0.03] px-2.5 text-[11px] text-foreground/55 transition-colors hover:border-accent-glow/30 hover:text-foreground/85 disabled:opacity-40"
          >
            {example}
          </button>
        ))}
      </div>
      <form onSubmit={submit} className="flex items-end gap-2">
        <div className="flex-1">
          <label htmlFor="studio-prompt" className="sr-only">
            Describe a change
          </label>
          <input
            id="studio-prompt"
            data-testid="studio-prompt"
            value={text}
            onChange={(event) => setText(event.target.value)}
            disabled={busy}
            maxLength={400}
            placeholder="Tell the studio what to change — color, mood, style, new element…"
            className="w-full rounded-lg border border-surface-border bg-white/[0.035] px-3.5 py-2.5 text-sm text-foreground outline-none placeholder:text-foreground/30 focus:border-accent-glow/45 focus:bg-white/[0.05] disabled:opacity-50"
          />
        </div>
        <Button type="submit" size="md" disabled={busy || !text.trim()} className="shrink-0">
          {busy ? "Working…" : "Apply"}
        </Button>
      </form>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] text-foreground/35">
          Natural language → typed scene commands · deterministic parser · no external model
        </p>
        {notice && (
          <button
            type="button"
            role={notice.kind === "error" ? "alert" : "status"}
            aria-live={notice.kind === "error" ? "assertive" : "polite"}
            onClick={onClearNotice}
            className={`max-w-full truncate rounded-md border px-2 py-1 text-left text-[11px] ${NOTICE_STYLES[notice.kind]}`}
            title="Dismiss"
          >
            {notice.text}
          </button>
        )}
      </div>
    </div>
  );
}
