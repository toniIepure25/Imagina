"use client";

import dynamic from "next/dynamic";

const DatasetReadinessPanel = dynamic(
  () => import("@/components/Dataset/DatasetReadinessPanel"),
  { ssr: false }
);

export default function DatasetsPage() {
  return (
    <main className="flex-1 mx-auto w-full max-w-4xl p-6 lg:p-10 space-y-6">
      <div>
        <div className="text-[11px] uppercase tracking-[0.22em] text-accent-glow/70">
          Research Infrastructure
        </div>
        <h1 className="mt-2 text-3xl font-bold glow-text">Dataset Readiness</h1>
        <p className="mt-3 max-w-3xl text-sm text-foreground/60">
          Local-first dataset status. Real EEG files must be imported manually.
          No raw EEG samples are exposed. All metrics are experimental proxy estimates.
        </p>
      </div>
      <DatasetReadinessPanel />
    </main>
  );
}
