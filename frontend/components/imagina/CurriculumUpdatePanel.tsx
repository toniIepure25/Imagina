"use client";

interface CurriculumUpdate { current_focus: string; new_focus: string; reason_for_update: string; difficulty_adjustments: Array<{dimension: string; delta: number}>; should_regenerate_task_plan: boolean; scientific_boundary?: string; }

export function CurriculumUpdatePanel({ update, onTrigger, onRefresh }: { update: CurriculumUpdate | null; onTrigger: () => void; onRefresh: () => void }) {
  if (!update) return (
    <div className="glass panel-glow p-4 space-y-3 text-[11px] border-l-2 border-amber-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Curriculum (V21)</div>
      <div className="text-foreground/50">Build a skill model to get curriculum recommendations.</div>
      <button onClick={onTrigger} className="px-3 py-1.5 rounded bg-lock/10 border border-amber-500/30 text-lock hover:bg-amber-500/30">Update Curriculum</button>
    </div>
  );
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[11px] border-l-2 border-amber-500/50">
      <div className="flex justify-between"><div className="text-foreground/40 uppercase tracking-[0.1em]">Curriculum (V21)</div></div>
      <div className="text-foreground/50">Focus: <span className="text-lock">{update.current_focus?.replace(/_/g, " ")} → {update.new_focus?.replace(/_/g, " ")}</span></div>
      <div className="text-foreground/40 text-[11px]">{update.reason_for_update}</div>
      {update.difficulty_adjustments?.map((a,i) => (
        <div key={i} className="text-foreground/30 text-[11px]">{a.dimension}: {a.delta > 0 ? "↑" : "↓"}{Math.abs(a.delta)}</div>
      ))}
      <button onClick={onTrigger} className="px-3 py-1.5 rounded bg-lock/10 border border-amber-500/30 text-lock hover:bg-amber-500/30">Re-analyze</button>
      <div className="text-foreground/20 text-[11px]">{update.scientific_boundary}</div>
    </div>
  );
}
