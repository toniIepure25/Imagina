"use client";

interface DimProfile {
  score: number; n_tasks: number; confidence: string; interpretation: string;
}

interface Phenotype {
  phenotype_label: string; phenotype_interpretation: string;
  n_completed_sessions: number;
  profile: Record<string, DimProfile>;
  strongest_dimensions: string[]; weakest_dimensions: string[];
  recommended_next_dimension: string;
  scientific_boundary?: string;
}

interface IPPProps { phenotype: Phenotype | null; onRefresh: () => void; onShowGaps: () => void; }

const CONF_COLORS: Record<string, string> = {
  high: "text-green-400", medium: "text-amber-400", low: "text-foreground/40", none: "text-foreground/20",
};

export function ImageryPhenotypePanel({ phenotype, onRefresh, onShowGaps }: IPPProps) {
  if (!phenotype || phenotype.n_completed_sessions < 1) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-lime-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Imagery Phenotype (V19)</div>
        <div className="text-foreground/50">Complete at least one imagery task session to build your phenotype.</div>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>
    );
  }

  const profile = phenotype.profile || {};

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-lime-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Imagery Phenotype (V19)</div>
        <span className="text-lime-400">{phenotype.phenotype_label?.replace(/_/g, " ")}</span>
      </div>

      <div className="text-foreground/40 text-[9px]">{phenotype.phenotype_interpretation?.slice(0, 100)}</div>

      <div className="space-y-1">
        {Object.entries(profile).map(([dim, d]) => (
          <div key={dim} className="flex gap-2 text-[8px] items-center">
            <span className="text-foreground/40 w-24 truncate">{dim.replace(/_/g, " ")}</span>
            <div className="flex-1 bg-surface-border rounded h-1.5">
              <div className="bg-lime-400 h-1.5 rounded" style={{ width: `${(d.score || 0) * 100}%` }} />
            </div>
            <span className="text-foreground/30 w-8 text-right">{(d.score || 0).toFixed(2)}</span>
            <span className={`text-[7px] ${CONF_COLORS[d.confidence] || ""}`}>{d.confidence}</span>
          </div>
        ))}
      </div>

      {phenotype.strongest_dimensions?.length > 0 && (
        <div className="text-foreground/50 text-[9px]">Strongest: <span className="text-green-400">{phenotype.strongest_dimensions.join(", ").replace(/_/g, " ")}</span></div>
      )}
      {phenotype.weakest_dimensions?.length > 0 && (
        <div className="text-foreground/50 text-[9px]">Growth: <span className="text-amber-400">{phenotype.weakest_dimensions.join(", ").replace(/_/g, " ")}</span></div>
      )}

      <div className="text-foreground/50 text-[9px]">Next dim: <span className="text-lime-300">{phenotype.recommended_next_dimension?.replace(/_/g, " ")}</span></div>

      <div className="flex gap-2">
        <button onClick={onShowGaps} className="px-3 py-1.5 rounded bg-lime-500/20 border border-lime-500/30 text-lime-300 hover:bg-lime-500/30">
          Analyze Gaps
        </button>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>

      <div className="text-foreground/20 text-[7px]">{phenotype.scientific_boundary}</div>
    </div>
  );
}
