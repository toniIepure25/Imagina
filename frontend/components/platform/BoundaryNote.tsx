import type { ReactNode } from "react";
import { PLATFORM_BOUNDARY } from "@/lib/claims";

export default function BoundaryNote({ children }: { children?: ReactNode }) {
  return (
    <aside
      role="note"
      className="rounded-lg border border-lock/20 bg-lock/[0.045] px-4 py-3 text-xs leading-6 text-foreground/60"
    >
      <span className="mono-label mr-2 text-lock/80">Boundary</span>
      {children ?? PLATFORM_BOUNDARY}
    </aside>
  );
}
