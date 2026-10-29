import type { Metadata } from "next";
import { Suspense } from "react";
import AppShell from "@/components/layout/AppShell";
import StudyDesigner from "@/components/research/StudyDesigner";

export const metadata: Metadata = {
  title: "Study Designer",
  description:
    "Build a locked, versioned N-of-1 plan with explicit boundaries. A local planning artifact, not a registry entry or evidence of efficacy.",
};

export default function StudyDesignPage() {
  return (
    <AppShell>
      <Suspense
        fallback={
          <div className="mx-auto w-full max-w-[1320px] px-4 py-10 md:px-6">
            <p className="text-sm text-foreground/45">Loading the local study designer…</p>
          </div>
        }
      >
        <StudyDesigner />
      </Suspense>
    </AppShell>
  );
}
