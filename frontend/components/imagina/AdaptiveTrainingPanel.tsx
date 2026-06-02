"use client";

interface AdaptivePlan {
  plan_title: string; training_focus: string; plan_rationale: string;
  source: { mean_pid_v2: number; weakest_dimension: string; confidence_level: string; n_pid_sessions: number };
  daily_plan: Array<{ day: number; title: string; duration_minutes: number; success_criterion: string }>;
  checkpoint_schedule: Array<{ day: number; type: string; task_id: string }>;
  expected_change: { target_metric: string; desired_direction: string; minimum_meaningful_change: number };
  scientific_boundary?: string;
}

interface ATProps {
  plan: AdaptivePlan | null;
  improved: boolean | null;
  pidTrend: string;
  onGenerate: () => void;
  onRegenerate: () => void;
}

export function AdaptiveTrainingPanel({ plan, improved, pidTrend, onGenerate, onRegenerate }: ATProps) {
  if (!plan) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-violet-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Adaptive Training (V14)</div>
        <div className="text-foreground/50">No adaptive plan yet. Complete PID v2 calibrations first.</div>
        <button onClick={onGenerate} className="px-3 py-1.5 rounded bg-violet-500/20 border border-violet-500/30 text-violet-300 hover:bg-violet-500/30">
          Generate Plan
        </button>
      </div>
    );
  }

  const checkpoints = ["Baseline", "Midpoint", "Final"];
  const trendLabel = pidTrend === "improving" || pidTrend === "slightly_improving"
    ? "Improving" : pidTrend === "declining" || pidTrend === "slightly_declining"
    ? "Needs attention" : "Stable";

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-violet-500/50">
      <div className="flex justify-between items-center">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Adaptive Training (V14)</div>
        <span className={`px-2 py-0.5 rounded text-[8px] ${
          improved ? "bg-green-500/20 text-green-400" : pidTrend === "insufficient_data"
          ? "bg-gray-500/20 text-gray-400" : "bg-amber-500/20 text-amber-400"
        }`}>
          {improved ? "Improved" : pidTrend === "insufficient_data" ? "No data" : trendLabel}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="text-foreground/50">Plan: <span className="text-foreground">{plan.plan_title}</span></div>
        <div className="text-foreground/50">Focus: <span className="text-violet-400">{plan.training_focus?.replace(/_/g, " ") || "—"}</span></div>
        <div className="text-foreground/50">Mean PID: <span className="text-accent-glow">{plan.source?.mean_pid_v2?.toFixed(3) || "?"}</span></div>
        <div className="text-foreground/50">Weakest: <span className="text-amber-400">{plan.source?.weakest_dimension?.replace(/_/g, " ") || "—"}</span></div>
      </div>

      <div className="text-foreground/40 text-[9px] leading-relaxed">{plan.plan_rationale}</div>

      <div className="space-y-1">
        <div className="text-foreground/50 tracking-[0.05em]">Daily Schedule</div>
        {plan.daily_plan?.slice(0, 7).map((d) => (
          <div key={d.day} className="flex gap-2 text-[9px] p-1.5 rounded bg-surface/30">
            <span className="text-foreground/30 w-6">D{d.day}</span>
            <span className="text-foreground/60 flex-1">{d.title}</span>
            <span className="text-foreground/30">{d.duration_minutes}m</span>
          </div>
        ))}
      </div>

      <div className="space-y-1">
        <div className="text-foreground/50 tracking-[0.05em]">Calibration Checkpoints</div>
        {plan.checkpoint_schedule?.map((cp, i) => (
          <div key={cp.day} className="flex gap-2 text-[9px] p-1.5 rounded bg-surface/30">
            <span className="text-violet-400">{checkpoints[i] || cp.type}</span>
            <span className="text-foreground/30">Day {cp.day}</span>
            <span className="text-foreground/40 ml-auto font-mono">{cp.task_id}</span>
          </div>
        ))}
      </div>

      <div className="text-foreground/30 text-[9px]">
        Expected: {plan.expected_change?.target_metric} {plan.expected_change?.desired_direction} by &ge;{plan.expected_change?.minimum_meaningful_change}
      </div>

      <div className="flex gap-2">
        <button onClick={onRegenerate} className="px-3 py-1.5 rounded bg-violet-500/20 border border-violet-500/30 text-violet-300 hover:bg-violet-500/30">
          Regenerate
        </button>
        <button onClick={onGenerate} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>

      <div className="text-foreground/20 text-[7px] leading-relaxed">{plan.scientific_boundary}</div>
    </div>
  );
}
