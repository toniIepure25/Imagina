"use client";

interface Milestone { milestone_id: string; title: string; description: string; achieved: boolean; achieved_at: string | null; }
interface Milestones { achieved_milestones: Milestone[]; pending_milestones: Milestone[]; latest_milestone: Milestone | null; next_recommended_milestone: Milestone | null; scientific_boundary?: string; }

export function MasteryMilestonesPanel({ milestones, onRefresh }: { milestones: Milestones | null; onRefresh: () => void }) {
  if (!milestones || (milestones.achieved_milestones?.length === 0 && milestones.pending_milestones?.length === 0)) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-yellow-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Milestones (V21)</div>
        <div className="text-foreground/50">Complete sessions to unlock milestones.</div>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      </div>
    );
  }
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-yellow-500/50">
      <div className="flex justify-between"><div className="text-foreground/40 uppercase tracking-[0.1em]">Milestones (V21)</div><span className="text-yellow-400">{milestones.achieved_milestones?.length || 0}/{ (milestones.achieved_milestones?.length||0) + (milestones.pending_milestones?.length||0)}</span></div>
      <div className="space-y-1 max-h-32 overflow-y-auto">
        {milestones.achieved_milestones?.slice(-5).map(m => (
          <div key={m.milestone_id} className="text-[8px] p-1 rounded bg-yellow-500/10 text-yellow-300 flex justify-between">
            <span>✓ {m.title}</span><span className="text-foreground/30">{m.achieved_at?.slice(0, 10)}</span>
          </div>
        ))}
      </div>
      {milestones.next_recommended_milestone && (
        <div className="text-foreground/50 text-[9px]">Next: <span className="text-yellow-300">{milestones.next_recommended_milestone.title}</span></div>
      )}
      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      <div className="text-foreground/20 text-[7px]">{milestones.scientific_boundary}</div>
    </div>
  );
}
