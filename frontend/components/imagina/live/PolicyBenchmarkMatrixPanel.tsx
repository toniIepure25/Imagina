"use client";

interface Matrix { ranked_policies?: Array<{ rank: number; policy_id: string; title?: string; grade?: string; score?: number }>; best_policy_id?: string; }

export function PolicyBenchmarkMatrixPanel({ matrix, onRunMatrix, onRefresh }: {
  matrix: Matrix | null; onRunMatrix: () => void; onRefresh: () => void;
}) {
  if (!matrix) return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-violet-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Policy Matrix (V41)</div>
      <div className="text-foreground/50">Run a matrix to rank policies.</div>
      <div className="flex gap-2">
        <button onClick={onRunMatrix} className="px-3 py-1.5 rounded bg-violet-500/20 border border-violet-500/30 text-violet-300 hover:bg-violet-500/30">Run Matrix</button>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      </div>
      <div className="text-foreground/20 text-[7px]">Comparing deterministic policy behavior. Not clinical, not BCI.</div>
    </div>
  );
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-violet-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Policy Matrix (V41)</div>
      <div className="space-y-1">
        {(matrix.ranked_policies || []).slice(0, 6).map(p => (
          <div key={p.policy_id} className="flex gap-2 text-[8px] p-1.5 rounded bg-surface/30 items-center">
            <span className="text-foreground/40">#{p.rank}</span>
            <span className="text-foreground/60 flex-1">{p.title || p.policy_id}</span>
            <span className={`px-1 py-0.5 rounded ${p.grade === "A" ? "bg-green-500/20 text-green-400" : "bg-amber-500/20 text-amber-400"}`}>{p.grade} · {(p.score || 0).toFixed(0)}</span>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <button onClick={onRunMatrix} className="px-3 py-1.5 rounded bg-violet-500/20 border border-violet-500/30 text-violet-300 hover:bg-violet-500/30">Run Matrix</button>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      </div>
      <div className="text-foreground/20 text-[7px]">Comparing deterministic policy behavior. Not clinical, not BCI.</div>
    </div>
  );
}
