"use client";

import { useState } from "react";

export function PolicyLabExportPanel({ onExport }: { onExport: () => Promise<Record<string, unknown> | null> }) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-cyan-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Policy Export (V41)</div>
      <button onClick={async () => { const r = await onExport(); if (r) setResult(r); }} className="px-3 py-1.5 rounded bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/30">Export Policy Pack</button>
      {result && <div className="text-foreground/30 text-[7px]">raw_eeg: {String(result.raw_eeg_included || false)} · safe: {String(result.safe_to_share || true)}</div>}
      <div className="text-foreground/30 text-[7px]">Policy schemas, profiles, matrix, leaderboard, safety boundaries. No raw EEG.</div>
    </div>
  );
}
