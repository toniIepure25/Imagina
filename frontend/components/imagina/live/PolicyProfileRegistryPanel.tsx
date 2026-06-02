"use client";

export function PolicyProfileRegistryPanel({ policies, onRun, onRefresh }: {
  policies: Array<{ policy_id: string; title?: string; origin?: string }>;
  onRun: (pid: string) => void; onRefresh: () => void;
}) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-pink-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Policy Registry (V41)</div>
      <div className="space-y-1 max-h-32 overflow-y-auto">
        {policies.map(p => (
          <div key={p.policy_id} className="flex gap-2 text-[8px] p-1.5 rounded bg-surface/30 items-center">
            <span className="text-foreground/40">{p.origin === "builtin" ? "B" : "I"}</span>
            <span className="text-foreground/60 flex-1 truncate">{p.title || p.policy_id}</span>
            <button onClick={() => onRun(p.policy_id)} className="px-2 py-0.5 rounded bg-indigo-500/20 border border-indigo-500/30 text-indigo-300">Run</button>
          </div>
        ))}
      </div>
      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
    </div>
  );
}
