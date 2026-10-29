"use client";

import { usePathname } from "next/navigation";
import { evidenceForSurface } from "@/lib/evidence/registry";
import { useGlassBox } from "./GlassBoxContext";
import EvidenceMark from "./EvidenceMark";

export default function EvidenceRail({ className = "" }: { className?: string }) {
  const pathname = usePathname();
  const { enabled } = useGlassBox();
  const entries = evidenceForSurface(pathname);
  if (!enabled || entries.length === 0) return null;

  return (
    <aside className={`border-t border-surface-border pt-4 ${className}`} aria-label="Evidence on this page">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <p className="mono-label text-foreground/35">Evidence on this page</p>
        {entries.map((entry) => (
          <span key={entry.id} className="flex items-center gap-1.5 text-[11px] text-foreground/50">
            <EvidenceMark evidenceId={entry.id} />
            {entry.label}
          </span>
        ))}
        <a href="/method" className="text-[11px] text-signal/75 underline-offset-4 hover:underline">
          Method &amp; Claim Atlas
        </a>
      </div>
    </aside>
  );
}
