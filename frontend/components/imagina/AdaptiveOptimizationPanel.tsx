"use client";

interface FocusModel {
  response_score: number; n_executions: number; mean_pid_change: number;
  mean_fatigue: number; mean_adherence: number; confidence_level: string;
  interpretation: string;
}

interface ResponseModel {
  best_focus: string; worst_focus: string; focus_models: Record<string, FocusModel>;
  n_executions: number; model_reliability: string;
  scientific_boundary?: string;
}

interface OptimizationRec {
  recommendation_type: string; recommended_focus: string; why: string[];
  confidence_level: string; scientific_boundary?: string;
}

interface FatigueModel {
  fatigue: { risk_level: string; average: number };
  adherence: { risk_level: string; average: number };
  recommended_session_length_minutes: number;
  recommendations: string[];
  scientific_boundary?: string;
}

interface AOPProps {
  responseModel: ResponseModel | null;
  optimizationRec: OptimizationRec | null;
  fatigueModel: FatigueModel | null;
  onRefresh: () => void;
  onGeneratePlan: () => void;
}

const RISK_COLORS: Record<string, string> = {
  high: "text-red-400 bg-red-500/10", medium: "text-amber-400 bg-amber-500/10",
  low: "text-green-400 bg-green-500/10",
};

export function AdaptiveOptimizationPanel({ responseModel, optimizationRec, fatigueModel, onRefresh, onGeneratePlan }: AOPProps) {
  if (!responseModel || responseModel.n_executions < 2) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-rose-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Adaptive Optimization (V16)</div>
        <div className="text-foreground/50">Complete at least 2 training executions for optimization insights.</div>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>
    );
  }

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-rose-500/50">
      <div className="flex justify-between items-center">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Adaptive Optimization (V16)</div>
        <span className="text-foreground/30 text-[8px]">{responseModel.model_reliability} reliability</span>
      </div>

      {fatigueModel && (
        <div className="grid grid-cols-2 gap-2">
          <div className="p-2 rounded bg-surface/30">
            <div className="text-foreground/30 text-[7px]">Fatigue</div>
            <span className={`px-1.5 py-0.5 rounded text-[8px] ${RISK_COLORS[fatigueModel.fatigue?.risk_level] || ""}`}>
              {fatigueModel.fatigue?.risk_level} ({fatigueModel.fatigue?.average}/10)
            </span>
          </div>
          <div className="p-2 rounded bg-surface/30">
            <div className="text-foreground/30 text-[7px]">Adherence</div>
            <span className={`px-1.5 py-0.5 rounded text-[8px] ${RISK_COLORS[fatigueModel.adherence?.risk_level] || ""}`}>
              {fatigueModel.adherence?.risk_level} ({(fatigueModel.adherence?.average * 100 || 0).toFixed(0)}%)
            </span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        <div className="p-1.5 rounded bg-surface/30">
          <div className="text-foreground/30 text-[7px]">Best Focus</div>
          <div className="text-green-400 text-[9px]">{responseModel.best_focus?.replace(/_/g, " ") || "—"}</div>
        </div>
        <div className="p-1.5 rounded bg-surface/30">
          <div className="text-foreground/30 text-[7px]">Worst Focus</div>
          <div className="text-amber-400 text-[9px]">{responseModel.worst_focus?.replace(/_/g, " ") || "—"}</div>
        </div>
      </div>

      {responseModel.focus_models && Object.keys(responseModel.focus_models).length > 0 && (
        <div className="space-y-1 max-h-40 overflow-y-auto">
          <div className="text-foreground/40 text-[8px] tracking-[0.05em]">Response Scores</div>
          {Object.entries(responseModel.focus_models).map(([focus, m]) => (
            <div key={focus} className="flex gap-2 text-[8px] p-1.5 rounded bg-surface/30">
              <span className="text-foreground/50 w-24 truncate">{focus.replace(/_/g, " ")}</span>
              <div className="flex-1 bg-surface-border rounded h-2 mt-1">
                <div className="bg-rose-400 h-2 rounded" style={{ width: `${(m.response_score || 0) * 100}%` }} />
              </div>
              <span className="text-foreground/30 w-8 text-right">{(m.response_score || 0).toFixed(2)}</span>
              <span className="text-foreground/20">x{m.n_executions}</span>
            </div>
          ))}
        </div>
      )}

      {optimizationRec && optimizationRec.recommendation_type !== "insufficient_data" && (
        <div className="p-2 rounded bg-rose-500/10 space-y-1">
          <div className="text-foreground/50 text-[9px]">
            Next: <span className="text-rose-300">{optimizationRec.recommended_focus?.replace(/_/g, " ")}</span>
            <span className="text-foreground/30 ml-1">({optimizationRec.recommendation_type})</span>
          </div>
          {optimizationRec.why?.slice(0, 2).map((r, i) => (
            <div key={i} className="text-foreground/40 text-[8px]">{r}</div>
          ))}
        </div>
      )}

      {fatigueModel?.recommendations && (
        <div className="text-foreground/40 text-[8px] leading-relaxed p-1.5 rounded bg-surface/20">
          {fatigueModel.recommendations.slice(0, 2).join(" ")}
        </div>
      )}

      <div className="flex gap-2">
        <button onClick={onGeneratePlan} className="px-3 py-1.5 rounded bg-rose-500/20 border border-rose-500/30 text-rose-300 hover:bg-rose-500/30">
          Generate Optimized Plan
        </button>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>

      <div className="text-foreground/20 text-[7px]">{responseModel.scientific_boundary}</div>
    </div>
  );
}
