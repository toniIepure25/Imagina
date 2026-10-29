"use client";

interface Evidence {
  evidence_score: number; category: string; safe_claim: string;
  component_scores: {
    pid_effect_strength: number; adherence_quality: number;
    fatigue_control: number; checkpoint_completeness: number;
    design_strength: number; confound_penalty: number;
  };
  main_limitations: string[];
  scientific_boundary?: string;
}

interface NEPProps {
  evidence: Evidence | null;
  onRefresh: () => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  very_strong_personal_signal: "bg-signal/10 text-signal",
  strong_personal_signal: "bg-signal/10 text-signal",
  promising_personal_signal: "bg-lock/10 text-lock",
  exploratory_signal: "bg-orange-500/20 text-lock",
  weak_evidence: "bg-danger/10 text-danger",
  insufficient_data: "bg-foreground/10 text-foreground/50",
};

export function NOf1EvidencePanel({ evidence, onRefresh }: NEPProps) {
  if (!evidence) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[11px] border-l-2 border-yellow-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">N-of-1 Evidence (V17)</div>
        <div className="text-foreground/50">Complete an experiment to see evidence scoring.</div>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>
    );
  }

  const comp = evidence.component_scores || {};
  const maxScores = { pid_effect_strength: 35, adherence_quality: 20, fatigue_control: 15, checkpoint_completeness: 15, design_strength: 15 };

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[11px] border-l-2 border-yellow-500/50">
      <div className="flex justify-between items-center">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">N-of-1 Evidence (V17)</div>
        <span className={`px-2 py-0.5 rounded text-[11px] ${CATEGORY_COLORS[evidence.category] || ""}`}>
          {evidence.evidence_score}/100
        </span>
      </div>

      <div className={`px-2 py-1 rounded text-[11px] ${CATEGORY_COLORS[evidence.category] || ""}`}>
        {evidence.category?.replace(/_/g, " ")}
      </div>

      <div className="space-y-1">
        {Object.entries(comp).filter(([k]) => k !== "confound_penalty").map(([key, val]) => (
          <div key={key} className="flex gap-2 text-[11px] items-center">
            <span className="text-foreground/40 w-24">{key.replace(/_/g, " ")}</span>
            <div className="flex-1 bg-surface-border rounded h-1.5">
              <div className="bg-lock h-1.5 rounded" style={{ width: `${((val || 0) / (maxScores[key as keyof typeof maxScores] || 1)) * 100}%` }} />
            </div>
            <span className="text-foreground/30 w-10 text-right">{val}/{maxScores[key as keyof typeof maxScores]}</span>
          </div>
        ))}
        {comp.confound_penalty > 0 && (
          <div className="text-danger text-[11px]">Confound penalty: -{comp.confound_penalty}</div>
        )}
      </div>

      <div className="text-foreground/40 text-[11px] leading-relaxed p-2 rounded bg-surface/20">
        {evidence.safe_claim}
      </div>

      {evidence.main_limitations && evidence.main_limitations.length > 0 && (
        <div className="space-y-0.5">
          <div className="text-foreground/50 text-[11px]">Limitations</div>
          {evidence.main_limitations.slice(0, 3).map((l, i) => (
            <div key={i} className="text-foreground/30 text-[11px]">{l}</div>
          ))}
        </div>
      )}

      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
        Refresh
      </button>

      <div className="text-foreground/20 text-[11px]">{evidence.scientific_boundary}</div>
    </div>
  );
}
