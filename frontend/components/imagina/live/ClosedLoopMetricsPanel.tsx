"use client";

interface Metrics { closed_loop_benchmark_score: number; grade: string; grade_reason: string; scene_responsiveness_score: number; policy_consistency_score: number; safety_gate_compliance_score: number; replay_quality_score: number; export_safety_score: number; warnings: string[]; scientific_boundary?: string; }

export function ClosedLoopMetricsPanel({ metrics, onBuild, onRefresh }: { metrics: Metrics | null; onBuild: () => void; onRefresh: () => void }) {
  if (!metrics) return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-violet-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">CL Metrics (V36)</div>
      <div className="text-foreground/50">Run benchmark suite to see metrics.</div>
      <button onClick={onBuild} className="px-3 py-1.5 rounded bg-violet-500/20 border border-violet-500/30 text-violet-300 hover:bg-violet-500/30">Build Metrics</button>
    </div>
  );
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-violet-500/50">
      <div className="flex justify-between"><div className="text-foreground/40 uppercase tracking-[0.1em]">CL Metrics (V36)</div>
      <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${metrics.grade === "A" ? "bg-green-500/20 text-green-400" : "bg-emerald-500/20 text-emerald-400"}`}>{metrics.grade} · {Math.round(metrics.closed_loop_benchmark_score)}/100</span></div>
      {(["scene_responsiveness_score", "policy_consistency_score", "safety_gate_compliance_score", "replay_quality_score", "export_safety_score"] as const).map(k => (
        <div key={k} className="flex gap-2 text-[8px] items-center">
          <span className="text-foreground/40 w-28">{k.replace(/_/g, " ")}</span>
          <div className="flex-1 bg-surface-border rounded h-1.5"><div className="bg-violet-400 h-1.5 rounded" style={{ width: `${metrics[k] || 0}%` }} /></div>
          <span className="text-foreground/30 w-10 text-right">{metrics[k] || 0}</span>
        </div>
      ))}
      <div className="text-foreground/40 text-[8px]">{metrics.grade_reason}</div>
      {metrics.warnings?.length > 0 && <div className="text-amber-400 text-[8px]">{metrics.warnings.join("; ")}</div>}
      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      <div className="text-foreground/20 text-[7px]">{metrics.scientific_boundary}</div>
    </div>
  );
}
