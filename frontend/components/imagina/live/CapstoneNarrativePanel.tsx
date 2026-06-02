"use client";

export function CapstoneNarrativePanel({ onBuild, onRefresh }: {
  onBuild: () => Promise<unknown>; onRefresh: () => void;
}) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-cyan-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Narrative (V44)</div>
      <div className="text-foreground/50 text-[9px]">Generates a reviewer-friendly markdown explaining IMAGINA systems and safety boundaries.</div>
      <div className="text-foreground/30 text-[7px]">Professional narrative with safe claim and forbidden claims list.</div>
      <div className="flex gap-2">
        <button onClick={onBuild} className="px-3 py-1.5 rounded bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/30">Build Narrative</button>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      </div>
    </div>
  );
}
