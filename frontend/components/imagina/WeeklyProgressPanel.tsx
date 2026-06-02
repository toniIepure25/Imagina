"use client";

interface WeeklyReport { n_guided_sessions: number; practice_consistency: number; average_iqi_proxy: number; average_pid_proxy: number; most_trained_dimension: string; most_improved_dimension: string; recommended_next_week_focus: string; summary_markdown: string; scientific_boundary?: string; }

export function WeeklyProgressPanel({ report, onGenerate, onRefresh }: { report: WeeklyReport | null; onGenerate: () => void; onRefresh: () => void }) {
  if (!report) return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-blue-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Weekly Report (V21)</div>
      <div className="text-foreground/50">Complete guided sessions during the week for a report.</div>
      <button onClick={onGenerate} className="px-3 py-1.5 rounded bg-blue-500/20 border border-blue-500/30 text-blue-300 hover:bg-blue-500/30">Generate Report</button>
    </div>
  );
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-blue-500/50">
      <div className="flex justify-between"><div className="text-foreground/40 uppercase tracking-[0.1em]">Weekly Report (V21)</div><span className="text-foreground/30">{report.n_guided_sessions} sessions</span></div>
      <div className="grid grid-cols-2 gap-1 text-[8px]">
        {[["IQI", report.average_iqi_proxy], ["PID", report.average_pid_proxy], ["Consistency", report.practice_consistency], ["Focus", report.most_trained_dimension?.replace(/_/g," ")]].map(([k,v]) => (
          <div key={k} className="p-1 rounded bg-surface/30"><span className="text-foreground/30">{k}</span><br /><span className="text-foreground/60">{typeof v === "number" ? v.toFixed(2) : String(v||"—")}</span></div>
        ))}
      </div>
      <div className="text-foreground/50">Next: <span className="text-blue-400">{report.recommended_next_week_focus?.replace(/_/g, " ")}</span></div>
      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      <div className="text-foreground/20 text-[7px]">{report.scientific_boundary}</div>
    </div>
  );
}
