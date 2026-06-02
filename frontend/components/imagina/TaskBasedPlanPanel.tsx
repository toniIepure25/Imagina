"use client";

interface DailyTask {
  day: number; task_id: string; task_title: string; target_dimension: string;
  prompt: string; duration_seconds: number; difficulty: number; why_chosen: string;
}

interface TaskPlan {
  plan_id: string; plan_type: string; phenotype_label: string; primary_gap: string;
  target_dimensions: string[]; daily_tasks: DailyTask[];
  expected_outcome: string; scientific_boundary?: string;
}

interface TPPProps { plan: TaskPlan | null; onRefresh: () => void; }

export function TaskBasedPlanPanel({ plan, onRefresh }: TPPProps) {
  if (!plan || !plan.daily_tasks || plan.daily_tasks.length === 0) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-teal-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Task Plan (V19)</div>
        <div className="text-foreground/50">Generate a task-based imagery training plan to see your daily schedule.</div>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>
    );
  }

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-teal-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Task Plan (V19)</div>
        <span className="text-foreground/30 text-[8px]">{plan.daily_tasks.length} days</span>
      </div>

      <div className="text-foreground/50 text-[9px]">Gap: <span className="text-teal-400">{plan.primary_gap?.replace(/_/g, " ")}</span></div>
      <div className="text-foreground/50 text-[9px]">Phenotype: <span className="text-teal-300">{plan.phenotype_label?.replace(/_/g, " ")}</span></div>

      <div className="space-y-1 max-h-56 overflow-y-auto">
        {plan.daily_tasks.map(d => (
          <div key={d.day} className="p-1.5 rounded bg-surface/30 space-y-0.5 text-[8px]">
            <div className="flex justify-between">
              <span className="text-foreground/50">Day {d.day}: {d.task_title}</span>
              <span className="text-foreground/30">L{d.difficulty} · {Math.round(d.duration_seconds / 60)}m</span>
            </div>
            <div className="text-foreground/40">Target: {d.target_dimension?.replace(/_/g, " ")}</div>
            <div className="text-foreground/30">{d.why_chosen?.slice(0, 80)}</div>
          </div>
        ))}
      </div>

      <div className="text-foreground/30 text-[8px]">{plan.expected_outcome?.slice(0, 100)}</div>

      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
        Refresh
      </button>

      <div className="text-foreground/20 text-[7px]">{plan.scientific_boundary}</div>
    </div>
  );
}
