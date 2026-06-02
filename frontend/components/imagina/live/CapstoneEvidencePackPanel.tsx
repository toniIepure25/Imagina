"use client";

export function CapstoneEvidencePackPanel({ pack, onBuild, onRefresh }: {
  pack: { n_files: number; safe_to_share: boolean; raw_eeg_included: boolean } | null;
  onBuild: () => Promise<unknown>; onRefresh: () => void;
}) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-violet-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Evidence Pack (V44)</div>
      {pack ? (
        <div className="space-y-1 text-[8px]">
          <div className="flex gap-2">
            <span className="px-1.5 py-0.5 rounded bg-green-500/20 text-green-400">Safe: {String(pack.safe_to_share)}</span>
            <span className="px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-400">raw_eeg: {String(pack.raw_eeg_included)}</span>
          </div>
          <div className="text-violet-300">{pack.n_files} files</div>
        </div>
      ) : (
        <div className="text-foreground/50">Build after running the capstone demo.</div>
      )}
      <div className="text-foreground/30 text-[7px]">Summaries only. No raw EEG, no raw notes, no BCI claims.</div>
      <button onClick={onBuild} className="px-3 py-1.5 rounded bg-violet-500/20 border border-violet-500/30 text-violet-300 hover:bg-violet-500/30">Build Pack</button>
    </div>
  );
}
