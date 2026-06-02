"use client";

interface ExecMetrics {
  execution_id: string; plan_title: string; training_focus: string;
  pid_change: number; adherence: number; avg_fatigue: number;
  avg_clarity: number; focus_quality: number; response_category: string;
}

interface Comparison {
  comparison_id: string; winner: string; confidence_level: string;
  metrics: {
    execution_a: ExecMetrics;
    execution_b: ExecMetrics;
    differences: { pid_change_delta: number; adherence_delta: number; fatigue_delta: number };
  };
  interpretation: string; scientific_boundary?: string;
}

interface FocusComparison {
  comparison: {
    ranked_focuses: Array<{ focus: string; response_score: number; n_executions: number }>;
    top_ranked: string;
    interpretation: string;
  };
  scientific_boundary?: string;
}

interface PCPProps {
  execComparison: Comparison | null;
  focusComparison: FocusComparison | null;
  onRefresh: () => void;
}

export function PlanComparisonPanel({ execComparison, focusComparison, onRefresh }: PCPProps) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-fuchsia-500/50">
      <div className="flex justify-between items-center">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Plan Comparator (V16)</div>
      </div>

      {execComparison && execComparison.winner !== "inconclusive" ? (
        (() => {
          const winnerKey = execComparison.winner as keyof typeof execComparison.metrics;
          const winnerData = execComparison.metrics[winnerKey] as ExecMetrics | undefined;
          return (
        <div className="space-y-2">
          <div className="text-foreground/50 text-[9px]">
            Winner: <span className={`font-medium ${
              execComparison.winner === "execution_a" ? "text-green-400" : "text-violet-400"
            }`}>
              {execComparison.winner === "execution_a" ? "Plan A" : "Plan B"}
              ({winnerData?.training_focus?.replace(/_/g, " ")})
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[8px]">
            <div className="p-2 rounded bg-surface/30">
              <div className="text-foreground/30">Plan A</div>
              <div className="text-foreground/60">{execComparison.metrics.execution_a?.training_focus?.replace(/_/g, " ") || "—"}</div>
              <div className="text-foreground/50">PID: {execComparison.metrics.execution_a?.pid_change?.toFixed(3)}</div>
              <div className="text-foreground/40">Adh: {(execComparison.metrics.execution_a?.adherence * 100 || 0).toFixed(0)}%</div>
            </div>
            <div className="p-2 rounded bg-surface/30">
              <div className="text-foreground/30">Plan B</div>
              <div className="text-foreground/60">{execComparison.metrics.execution_b?.training_focus?.replace(/_/g, " ") || "—"}</div>
              <div className="text-foreground/50">PID: {execComparison.metrics.execution_b?.pid_change?.toFixed(3)}</div>
              <div className="text-foreground/40">Adh: {(execComparison.metrics.execution_b?.adherence * 100 || 0).toFixed(0)}%</div>
            </div>
          </div>

          <div className="text-foreground/30 text-[8px]">
            Delta: PID {execComparison.metrics.differences?.pid_change_delta?.toFixed(3)} ·
            Adh {execComparison.metrics.differences?.adherence_delta?.toFixed(3)} ·
            Conf: {execComparison.confidence_level}
          </div>

          <div className="text-foreground/40 text-[8px] leading-relaxed">{execComparison.interpretation}</div>
        </div>
          );
        })()
      ) : execComparison ? (
        <div className="text-foreground/50 text-[9px]">
          Results were inconclusive between the compared plans.
        </div>
      ) : (
        <div className="text-foreground/50">Complete 2+ executions to compare plans.</div>
      )}

      {focusComparison?.comparison?.ranked_focuses && focusComparison.comparison.ranked_focuses.length > 0 && (
        <div className="space-y-1">
          <div className="text-foreground/40 text-[8px] tracking-[0.05em]">Focus Rankings</div>
          {focusComparison.comparison.ranked_focuses.slice(0, 5).map((f, i) => (
            <div key={f.focus} className="flex gap-2 text-[8px] p-1 rounded bg-surface/30">
              <span className="text-foreground/30 w-4">#{i + 1}</span>
              <span className="text-foreground/50 flex-1">{f.focus.replace(/_/g, " ")}</span>
              <span className={`${i === 0 ? "text-green-400" : "text-foreground/30"}`}>
                {(f.response_score || 0).toFixed(2)}
              </span>
              <span className="text-foreground/20">x{f.n_executions}</span>
            </div>
          ))}
        </div>
      )}

      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
        Refresh Comparisons
      </button>

      <div className="text-foreground/20 text-[7px]">
        {execComparison?.scientific_boundary || focusComparison?.scientific_boundary}
      </div>
    </div>
  );
}
