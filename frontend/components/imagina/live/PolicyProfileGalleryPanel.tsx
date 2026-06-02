"use client";

interface GalleryPolicy {
  policy_id: string; title: string; policy_type?: string; description?: string;
  payload?: Record<string, unknown>;
  weights?: Record<string, number>; thresholds?: Record<string, number>;
}

interface GalleryProps { policies: GalleryPolicy[]; onLoadIntoEditor: (p: Record<string, unknown>) => void; onRunBenchmark: (pid: string) => void; }

const TRAIT_MAP: Record<string, string> = {
  balanced: "Equal weights, default behavior",
  clarity_first: "Clarity 1.5x, lower fatigue sensitivity",
  fatigue_protective: "Fatigue penalty 1.8x, early recovery",
  signal_strict: "Min SQI=0.75, limited deltas",
  recovery_first: "Quick pause, small scene changes",
  conservative_safe: "Most conservative, strict safety",
};

export function PolicyProfileGalleryPanel({ policies, onLoadIntoEditor, onRunBenchmark }: GalleryProps) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-fuchsia-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Policy Gallery (V41)</div>
        <span className="text-foreground/30 text-[8px]">{policies.length} profiles</span>
      </div>
      <div className="grid grid-cols-3 gap-2 max-h-64 overflow-y-auto">
        {policies.slice(0, 6).map(p => (
          <div key={p.policy_id} className="p-2 rounded bg-surface/30 space-y-1">
            <div className="text-foreground/60 text-[9px] font-medium">{p.title}</div>
            <div className="text-fuchsia-400 text-[7px]">{p.policy_type}</div>
            <div className="text-foreground/30 text-[7px]">{TRAIT_MAP[p.policy_type || "balanced"] || p.description?.slice(0, 40)}</div>
            <div className="flex gap-1">
              <button onClick={() => onLoadIntoEditor((p.payload || p) as Record<string, unknown>)} className="px-2 py-0.5 rounded bg-fuchsia-500/20 border border-fuchsia-500/30 text-fuchsia-300 text-[8px]">Edit</button>
              <button onClick={() => onRunBenchmark(p.policy_id)} className="px-2 py-0.5 rounded bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 text-[8px]">Run</button>
            </div>
          </div>
        ))}
      </div>
      <div className="text-foreground/20 text-[7px]">Policy profiles tune symbolic scene/session recommendations only.</div>
    </div>
  );
}
