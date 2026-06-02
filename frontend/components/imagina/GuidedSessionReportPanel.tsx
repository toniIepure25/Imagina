"use client";

interface SessionReport {
  task_title: string; task_category: string; status: string;
  summary: { n_checkins: number; avg_vividness: number; avg_stability: number;
    avg_effort: number; avg_fatigue: number; final_iqi_proxy: number; final_pid_proxy: number;
    phase_coverage: string; not_clinical?: boolean; };
  recommended_next_dimension: string; recommended_next_task: string;
  safety_notes: string[]; scientific_boundary?: string;
}

interface GSRProps { report: SessionReport | null; onExport: () => void; onRefresh: () => void; }

export function GuidedSessionReportPanel({ report, onExport, onRefresh }: GSRProps) {
  if (!report) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-violet-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Session Report (V20)</div>
        <div className="text-foreground/50">Complete a guided session to see its report.</div>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      </div>
    );
  }
  const s = report.summary || {} as SessionReport["summary"];
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-violet-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Session Report (V20)</div>
      <div className="text-foreground/60">{report.task_title}</div>
      <div className="grid grid-cols-3 gap-1 text-center text-[8px]">
        {[["Vivid", s.avg_vividness], ["Stab", s.avg_stability], ["Effort", s.avg_effort], ["Fatigue", s.avg_fatigue], ["IQI", s.final_iqi_proxy], ["PID", s.final_pid_proxy]].map(([k, v]) => (
          <div key={k} className="p-1 rounded bg-surface/30"><span className="text-foreground/30">{k}</span><br />          <span className="text-foreground/60">{typeof v === "number" ? v.toFixed(1) : String(v || "—")}</span></div>
        ))}
      </div>
      <div className="text-foreground/50 text-[9px]">Next: <span className="text-violet-400">{report.recommended_next_dimension?.replace(/_/g, " ")}</span></div>
      <div className="flex gap-2">
        <button onClick={onExport} className="px-3 py-1.5 rounded bg-violet-500/20 border border-violet-500/30 text-violet-300 hover:bg-violet-500/30">Export as Rating</button>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      </div>
      <div className="text-foreground/20 text-[7px]">{report.scientific_boundary}</div>
    </div>
  );
}
