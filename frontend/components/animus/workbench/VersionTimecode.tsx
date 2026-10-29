"use client";

import { useEffect, useRef } from "react";
import type { VersionSummary } from "@/lib/animusStudioApi";

const SOURCE_LABEL: Record<string, string> = {
  compose: "compose",
  refine: "prompt",
  "direct-edit": "edit",
  branch: "branch",
  regenerate: "variation",
};

function versionSource(source: string): string {
  return SOURCE_LABEL[source] ?? source;
}

export default function VersionTimecode({
  versions,
  activeVersionId,
  previewVersionId,
  busy,
  onPreview,
}: {
  versions: VersionSummary[];
  activeVersionId: string;
  previewVersionId: string | null;
  busy: boolean;
  onPreview: (versionId: string) => void;
}) {
  const ordered = versions.slice().sort((a, b) => a.number - b.number);
  const currentId = previewVersionId ?? activeVersionId;
  const currentRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    currentRef.current?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
  }, [currentId]);
  if (versions.length < 2) return null;
  return (
    <section
      aria-label="Scene timecode"
      data-testid="version-timecode"
      className="flex items-center gap-3 border-b border-white/[0.07] bg-[#06080b]/90 px-3 py-1.5"
    >
      <div className="shrink-0">
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-signal/65">Timecode</p>
        <p className="mt-0.5 hidden text-[11px] text-foreground/30 sm:block">Preview a version in place.</p>
      </div>
      <div className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto pb-0.5 [scrollbar-width:thin]">
        {ordered.map((version) => {
          const isHead = version.version_id === activeVersionId;
          const isCurrent = version.version_id === currentId;
          return (
            <button
              key={version.version_id}
              ref={isCurrent ? currentRef : undefined}
              type="button"
              disabled={busy}
              aria-pressed={isCurrent}
              aria-label={`Preview version ${version.number}: ${version.label}`}
              title={version.intention ?? version.label}
              onClick={() => onPreview(version.version_id)}
              className={`group flex shrink-0 items-center gap-1.5 rounded border px-2 py-1 text-left transition-colors disabled:opacity-40 ${
                isCurrent
                  ? "border-lock/45 bg-lock/[0.08] text-lock"
                  : "border-white/8 bg-white/[0.02] text-foreground/45 hover:border-white/20 hover:text-foreground/75"
              }`}
            >
              <span className="font-mono text-[11px]">v{version.number}</span>
              <span className="hidden max-w-[110px] truncate text-[11px] sm:block">{version.label}</span>
              <span className="font-mono text-[11px] uppercase tracking-[0.1em] text-foreground/25">
                {versionSource(version.source)}
              </span>
              {isHead ? (
                <span className="rounded-full border border-signal/30 px-1 font-mono text-[11px] uppercase text-signal/80">
                  head
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
      <span className="hidden shrink-0 font-mono text-[11px] uppercase tracking-[0.14em] text-foreground/25 md:block">
        {previewVersionId ? "previewing · not committed" : "live head"}
      </span>
    </section>
  );
}
