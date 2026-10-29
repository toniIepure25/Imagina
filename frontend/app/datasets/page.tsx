"use client";

import dynamic from "next/dynamic";
import AppShell from "@/components/layout/AppShell";
import PageHeader from "@/components/platform/PageHeader";
import BoundaryNote from "@/components/platform/BoundaryNote";
import EvidenceMark from "@/components/evidence/EvidenceMark";

const DatasetReadinessPanel = dynamic(() => import("@/components/Dataset/DatasetReadinessPanel"), {
  ssr: false,
  loading: () => (
    <div role="status" aria-busy="true" className="h-48 animate-pulse rounded-xl border border-white/10 bg-white/[0.025]" />
  ),
});

export default function DatasetsPage() {
  return (
    <AppShell>
      <div className="mx-auto w-full max-w-5xl space-y-6 px-4 py-8 md:px-6 lg:py-10">
        <PageHeader
          eyebrow="Research infrastructure"
          title="Dataset readiness"
          description="Local-first dataset status. Real EEG files must be imported manually. No raw EEG samples are exposed, and all metrics remain experimental proxy estimates."
          meta={
            <span className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.14em] text-foreground/35">
              Local SQLite · no external transfer
              <EvidenceMark evidenceId="dataset.readiness" />
            </span>
          }
        />
        <DatasetReadinessPanel />
        <BoundaryNote>
          Dataset presence is not evidence of signal validity. Imported files still require artifact review, channel
          checks, and a pre-registered analysis plan.
        </BoundaryNote>
      </div>
    </AppShell>
  );
}
