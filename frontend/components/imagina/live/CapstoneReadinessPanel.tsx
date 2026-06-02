"use client";

export function CapstoneReadinessPanel({ readiness, onCheck, onRefresh }: {
  readiness: Record<string, unknown> | null; onCheck: () => Promise<Record<string, unknown> | null>; onRefresh: () => void;
}) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-emerald-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Readiness (V44)</div>
        {readiness && (
          <span className={`px-2 py-0.5 rounded text-[8px] ${readiness.ready ? "bg-green-500/20 text-green-400" : "bg-amber-500/20 text-amber-400"}`}>
            {String(readiness.score || 0)} · {readiness.ready ? "Ready" : "Needs"}
          </span>
        )}
      </div>
      <div className="flex gap-2">
        <button onClick={async () => { await onCheck(); }} className="px-3 py-1.5 rounded bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/30">Check Readiness</button>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      </div>
    </div>
  );
}
