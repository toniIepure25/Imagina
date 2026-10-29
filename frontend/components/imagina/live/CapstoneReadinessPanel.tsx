"use client";

export function CapstoneReadinessPanel({ readiness, onCheck, onRefresh }: {
  readiness: Record<string, unknown> | null; onCheck: () => Promise<Record<string, unknown> | null>; onRefresh: () => void;
}) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[11px] border-l-2 border-emerald-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Readiness (V44)</div>
        {readiness && (
          <span className={`px-2 py-0.5 rounded text-[11px] ${readiness.ready ? "bg-signal/10 text-signal" : "bg-lock/10 text-lock"}`}>
            {String(readiness.score || 0)} · {readiness.ready ? "Ready" : "Needs"}
          </span>
        )}
      </div>
      <div className="flex gap-2">
        <button onClick={async () => { await onCheck(); }} className="px-3 py-1.5 rounded bg-signal/10 border border-signal/25 text-signal hover:bg-signal/20">Check Readiness</button>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      </div>
    </div>
  );
}
