"use client";

interface PlanRun {
  run: { plan_id: string; current_day: number; completed_days: number[];
    active_session_id: string | null; status: string; adherence_rate: number; };
}

interface GPRProps { progress: PlanRun | null; onStartNext: () => void; onCompleteDay: (sid: string) => void; onRefresh: () => void; }

export function GuidedPlanRunnerPanel({ progress, onStartNext, onCompleteDay, onRefresh }: GPRProps) {
  if (!progress || progress.run?.status === "completed") {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-amber-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Guided Plan Runner (V20)</div>
        <div className="text-foreground/50">{progress?.run?.status === "completed" ? "Plan completed!" : "Start a guided task from your plan."}</div>
        <div className="flex gap-2">
          {progress?.run?.status !== "completed" && <button onClick={onStartNext} className="px-3 py-1.5 rounded bg-amber-500/20 border border-amber-500/30 text-amber-300 hover:bg-amber-500/30">Start Next Task</button>}
          <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
        </div>
      </div>
    );
  }

  const r = progress.run;
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-amber-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Guided Plan Runner (V20)</div>
        <span className={`px-2 py-0.5 rounded text-[8px] ${r.status === "active" ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-400"}`}>{r.status}</span>
      </div>
      <div className="text-foreground/50">Day {r.current_day} · Adherence: {(r.adherence_rate * 100).toFixed(0)}%</div>
      <div className="text-foreground/50">Done: [{r.completed_days?.join(", ") || "—"}]</div>
      <div className="flex gap-2">
        {r.active_session_id && <button onClick={() => onCompleteDay(r.active_session_id!)} className="px-3 py-1.5 rounded bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/30">Complete Day</button>}
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      </div>
    </div>
  );
}
