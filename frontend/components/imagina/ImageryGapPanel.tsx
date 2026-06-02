"use client";

interface Gap {
  gap_id: string; dimension: string; severity: string; priority: number;
  recommended_training_focus: string; recommended_task_categories: string[];
  evidence: string[];
}

interface GapAnalysis {
  phenotype_label: string; primary_gap: string; secondary_gap: string;
  recommended_training_focus: string; ranked_gaps: Gap[];
  scientific_boundary?: string;
}

interface IGPProps { gaps: GapAnalysis | null; onGeneratePlan: () => void; onRefresh: () => void; }

const SEV_COLORS: Record<string, string> = {
  high: "text-red-400 bg-red-500/10", medium: "text-amber-400 bg-amber-500/10", low: "text-blue-400 bg-blue-500/10",
};

export function ImageryGapPanel({ gaps, onGeneratePlan, onRefresh }: IGPProps) {
  if (!gaps || !gaps.primary_gap) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-green-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Imagery Gaps (V19)</div>
        <div className="text-foreground/50">No gap analysis available. Build a phenotype first.</div>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>
    );
  }

  const ranked = gaps.ranked_gaps || [];

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-green-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Imagery Gaps (V19)</div>
        <span className="text-foreground/30 text-[8px]">{ranked.length} gaps</span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-[9px]">
        <div className="text-foreground/50">Primary: <span className="text-red-400">{gaps.primary_gap?.replace(/_/g, " ")}</span></div>
        <div className="text-foreground/50">Secondary: <span className="text-amber-400">{gaps.secondary_gap?.replace(/_/g, " ")}</span></div>
      </div>

      <div className="text-foreground/50 text-[9px]">Rec Focus: <span className="text-green-400">{gaps.recommended_training_focus?.replace(/_/g, " ")}</span></div>

      <div className="space-y-1 max-h-48 overflow-y-auto">
        {ranked.slice(0, 6).map(g => (
          <div key={g.gap_id} className="flex gap-2 text-[8px] p-1.5 rounded bg-surface/30 items-center">
            <span className={`px-1.5 py-0.5 rounded ${SEV_COLORS[g.severity] || ""}`}>{g.severity}</span>
            <span className="text-foreground/60 flex-1">{g.dimension?.replace(/_/g, " ")}</span>
            <span className="text-foreground/30">P{g.priority}</span>
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <button onClick={onGeneratePlan} className="px-3 py-1.5 rounded bg-green-500/20 border border-green-500/30 text-green-300 hover:bg-green-500/30">
          Generate Task Plan
        </button>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>

      <div className="text-foreground/20 text-[7px]">{gaps.scientific_boundary}</div>
    </div>
  );
}
