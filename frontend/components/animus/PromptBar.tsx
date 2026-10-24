"use client";

import { useState, type FormEvent } from "react";
import Button from "@/components/common/Button";
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

export default function PromptBar({
  busy,
  notice,
  onSubmit,
  onClearNotice,
}: {
  busy: boolean;
  notice: StudioNotice | null;
  onSubmit: (text: string) => Promise<unknown>;
  onClearNotice: () => void;
}) {
  const [text, setText] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const value = text.trim();
    if (!value || busy) return;
    const result = await onSubmit(value);
    if (result) setText("");
  };

  return (
    <div className="border-t border-surface-border bg-background/80 px-4 py-3 backdrop-blur">
      <div className="mb-2 flex gap-1.5 overflow-x-auto pb-1 [scrollbar-width:none]">
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            disabled={busy}
            onClick={() => setText(example)}
            className="shrink-0 rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[10px] text-foreground/50 transition-colors hover:border-accent-glow/30 hover:text-foreground/80 disabled:opacity-40"
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
            className="w-full rounded-lg border border-surface-border bg-white/[0.035] px-3.5 py-2.5 text-sm text-foreground outline-none placeholder:text-foreground/28 focus:border-accent-glow/45 focus:bg-white/[0.05] disabled:opacity-50"
          />
        </div>
        <Button type="submit" size="md" disabled={busy || !text.trim()} className="shrink-0">
          {busy ? "Working…" : "Apply"}
        </Button>
      </form>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-[10px] text-foreground/30">
          Natural language → typed scene commands · deterministic parser · no external model
        </p>
        {notice && (
          <button
            type="button"
            role={notice.kind === "error" ? "alert" : "status"}
            aria-live={notice.kind === "error" ? "assertive" : "polite"}
            onClick={onClearNotice}
            className={`max-w-full truncate rounded-md border px-2 py-1 text-left text-[10px] ${NOTICE_STYLES[notice.kind]}`}
            title="Dismiss"
          >
            {notice.text}
          </button>
        )}
      </div>
    </div>
  );
}
