"use client";

interface TimelineItem {
  type: string; date: string; pid_v2?: number; session_id?: string;
  plan_title?: string; adherence_rate?: number; response_category?: string;
}

interface LongitudinalReport {
  summary: {
    n_calibration_sessions: number; n_adaptive_plans: number; n_executions: number;
    current_pid_trend: string; best_training_focus: string; main_bottleneck: string;
    overall_training_response: string;
  };
  pid_summary: {
    n_sessions: number; first_pid?: number; latest_pid?: number;
    absolute_change?: number; meaningful_change?: boolean; trend?: string;
  };
  execution_summary: {
    n_executions: number; average_adherence?: number;
    best_training_focus?: string; average_fatigue?: number;
  };
  timeline: TimelineItem[];
  recommendations: string[];
  allowed_claim?: string;
  scientific_boundary?: string;
}

interface LPPProps {
  report: LongitudinalReport | null;
  onGenerate: () => void;
}

export function LongitudinalProgressPanel({ report, onGenerate }: LPPProps) {
  if (!report || report.summary.n_calibration_sessions + report.summary.n_executions < 1) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-indigo-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Longitudinal Progress (V15)</div>
        <div className="text-foreground/50">Not enough data for a progress report yet. Complete calibrations and training executions.</div>
        <button onClick={onGenerate} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Generate Report
        </button>
      </div>
    );
  }

  const s = report.summary;
  const ps = report.pid_summary;
  const es = report.execution_summary;

  const trendLabel = ps.trend === "improving" || ps.trend === "slightly_improving"
    ? "Improving" : ps.trend === "declining" || ps.trend === "slightly_declining"
    ? "Declining" : "Stable";

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-indigo-500/50">
      <div className="flex justify-between items-center">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Longitudinal Progress (V15)</div>
        <span className={`px-2 py-0.5 rounded text-[8px] ${
          ps.meaningful_change ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-400"
        }`}>
          {ps.meaningful_change ? "Meaningful" : "Minimal"}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="p-2 rounded bg-surface/30 text-center">
          <div className="text-foreground/30 text-[7px]">Calibrations</div>
          <div className="text-foreground">{s.n_calibration_sessions}</div>
        </div>
        <div className="p-2 rounded bg-surface/30 text-center">
          <div className="text-foreground/30 text-[7px]">Executions</div>
          <div className="text-foreground">{s.n_executions}</div>
        </div>
        <div className="p-2 rounded bg-surface/30 text-center">
          <div className="text-foreground/30 text-[7px]">PID Trend</div>
          <div className={`text-[9px] ${ps.trend?.includes("improving") ? "text-green-400" : ps.trend?.includes("declining") ? "text-amber-400" : "text-foreground/60"}`}>{trendLabel}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="text-foreground/50 text-[9px]">First PID: <span className="text-foreground">{ps.first_pid?.toFixed(3) || "—"}</span></div>
        <div className="text-foreground/50 text-[9px]">Latest PID: <span className="text-foreground">{ps.latest_pid?.toFixed(3) || "—"}</span></div>
        <div className="text-foreground/50 text-[9px]">Change: <span className={ps.absolute_change !== undefined && ps.absolute_change <= 0 ? "text-green-400" : "text-amber-400"}>
          {ps.absolute_change !== undefined ? (ps.absolute_change <= 0 ? "↓" : "↑") + Math.abs(ps.absolute_change).toFixed(3) : "—"}
        </span></div>
        <div className="text-foreground/50 text-[9px]">Adherence: <span className="text-foreground">
          {es.average_adherence != null ? (es.average_adherence * 100).toFixed(0) + "%" : "—"}
        </span></div>
      </div>

      {es.best_training_focus && (
        <div className="text-foreground/50 text-[9px]">Best Focus: <span className="text-green-400">{es.best_training_focus.replace(/_/g, " ")}</span></div>
      )}

      {report.timeline && report.timeline.length > 0 && (
        <div className="space-y-1 max-h-32 overflow-y-auto">
          <div className="text-foreground/40 text-[9px] tracking-[0.05em]">Timeline</div>
          {report.timeline.slice(0, 8).map((t, i) => (
            <div key={i} className="flex gap-2 text-[8px] p-1 rounded bg-surface/30">
              <span className={t.type === "calibration" ? "text-cyan-400" : "text-violet-400"}>
                {t.type === "calibration" ? "[C]" : "[E]"}
              </span>
              <span className="text-foreground/40">{t.date.slice(0, 10)}</span>
              <span className="text-foreground/60 truncate flex-1">
                {t.pid_v2 != null ? `PID:${t.pid_v2.toFixed(2)}` : t.plan_title?.slice(0, 25) || "—"}
              </span>
            </div>
          ))}
        </div>
      )}

      {report.recommendations && report.recommendations.length > 0 && (
        <div className="text-foreground/40 text-[8px] leading-relaxed p-2 rounded bg-surface/20">
          <span className="text-foreground/50">Recommendations:</span>
          <br />{report.recommendations.slice(0, 2).join(" ")}
        </div>
      )}

      <button onClick={onGenerate} className="px-3 py-1.5 rounded bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/30">
        Regenerate Report
      </button>

      <div className="text-foreground/20 text-[7px]">{report.scientific_boundary}</div>
    </div>
  );
}
