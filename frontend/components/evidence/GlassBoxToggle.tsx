"use client";

import { useGlassBox } from "./GlassBoxContext";

export default function GlassBoxToggle({ compact = false }: { compact?: boolean }) {
  const { enabled, setPreference } = useGlassBox();
  return (
    <button
      type="button"
      onClick={() => setPreference(enabled ? "off" : "on")}
      className="inline-flex h-11 items-center gap-2 rounded-lg border border-surface-border px-3 text-[11px] text-foreground/60 transition-colors hover:bg-white/[0.04] hover:text-foreground"
      aria-pressed={enabled}
      aria-label={enabled ? "Hide evidence marks" : "Show evidence marks"}
      title={enabled ? "Hide evidence marks" : "Show evidence marks"}
    >
      <span aria-hidden="true" className={enabled ? "text-signal" : "text-foreground/30"}>
        ◉
      </span>
      {compact ? null : <span>Evidence {enabled ? "on" : "off"}</span>}
    </button>
  );
}
