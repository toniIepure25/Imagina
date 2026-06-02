"use client";

import { useState } from "react";

interface SdkExport { n_files: number; export_dir: string; raw_eeg_included: boolean; safe_to_share: boolean; }

export function BenchmarkSdkExportPanel({ onExport, onRefresh }: { onExport: () => Promise<SdkExport | null>; onRefresh: () => void }) {
  const [result, setResult] = useState<SdkExport | null>(null);

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-violet-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">SDK Export (V39)</div>
        {result && <span className="text-violet-300 text-[8px]">{result.n_files} files</span>}
      </div>
      <button onClick={async () => { const r = await onExport(); if (r) setResult(r); }} className="px-3 py-1.5 rounded bg-violet-500/20 border border-violet-500/30 text-violet-300 hover:bg-violet-500/30">Export SDK Pack</button>
      {result && (
        <div className="space-y-1 text-[8px]">
          <div className="text-foreground/50">Dir: {result.export_dir?.slice(-30)}</div>
          <div className="flex gap-2">
            <span className="px-1.5 py-0.5 rounded bg-green-500/20 text-green-400">Safe: {String(result.safe_to_share)}</span>
            <span className="px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-400">raw_eeg: {String(result.raw_eeg_included)}</span>
          </div>
        </div>
      )}
      <div className="text-foreground/30 text-[8px]">Exports contain schemas, scenarios, suite summaries, and safety boundaries only. No raw EEG, no BCI claims, no neurofeedback validation.</div>
      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
    </div>
  );
}
