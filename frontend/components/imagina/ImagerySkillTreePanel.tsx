"use client";

interface DimSkill { current_level: number; level_name: string; unlock_progress: number; trend: string; n_sessions: number; confidence: string; }
interface SkillModel { dimensions: Record<string, DimSkill>; strongest_progress_dimension: string; highest_level_dimension: string; n_total_sessions: number; scientific_boundary?: string; }

export function ImagerySkillTreePanel({ model, onRefresh }: { model: SkillModel | null; onRefresh: () => void }) {
  if (!model || model.n_total_sessions < 2) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-green-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Skill Tree (V21)</div>
        <div className="text-foreground/50">Complete at least 2 sessions across dimensions to build your skill tree.</div>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      </div>
    );
  }
  const dims = model.dimensions || {};
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-green-500/50">
      <div className="flex justify-between"><div className="text-foreground/40 uppercase tracking-[0.1em]">Skill Tree (V21)</div><span className="text-foreground/30 text-[8px]">{model.n_total_sessions} sessions</span></div>
      <div className="space-y-1 max-h-64 overflow-y-auto">
        {Object.entries(dims).map(([dim, d]) => (
          <div key={dim} className="flex gap-2 text-[8px] items-center p-1">
            <span className="text-foreground/40 w-20">{dim.replace(/_/g, " ")}</span>
            <span className="text-green-400 w-6">L{d.current_level}</span>
            <div className="flex-1 bg-surface-border rounded h-1"><div className="bg-green-400 h-1 rounded" style={{ width: `${(d.unlock_progress || 0) * 100}%` }} /></div>
            <span className={`text-[7px] ${d.trend === "improving" ? "text-green-400" : d.trend === "declining" ? "text-red-400" : "text-foreground/30"}`}>{d.trend?.slice(0, 4)}</span>
          </div>
        ))}
      </div>
      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      <div className="text-foreground/20 text-[7px]">{model.scientific_boundary}</div>
    </div>
  );
}
