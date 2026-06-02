"use client";

import { useState } from "react";

interface DayEntry {
  day: number; status: string;
  planned_exercise: { title: string; duration_minutes: number; target_dimension: string };
  requires_calibration: boolean; calibration_task_id: string | null;
  checkin: { difficulty_rating: number; clarity_rating: number; fatigue_rating: number; focus_quality: number } | null;
  calibration_session_id: string | null; checkpoint_pid: number | null;
}

interface Execution {
  execution_id: string; status: string; plan_title: string; training_focus: string;
  started_at: string; days: DayEntry[];
  summary: { completed_days: number; skipped_days: number; pending_days: number; total_days: number; adherence_rate: number };
  scientific_boundary?: string;
}

interface Analysis {
  response_category: string; confidence_level: string; interpretation: string;
  adherence: { adherence_rate: number };
  pid_checkpoint_analysis?: { baseline_to_final_change?: number; meaningful_improvement?: boolean; checkpoint_pid_values?: Array<{day: number; pid_v2: number}> };
  subjective_metrics?: { avg_fatigue: number; avg_focus_quality: number; avg_clarity: number };
}

interface AEPProps {
  execution: Execution | null;
  analysis: Analysis | null;
  onStart: () => void;
  onCompleteDay: (day: number, payload: Record<string, unknown>) => void;
  onClose: () => void;
  onRefresh: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-500/20 text-gray-400",
  completed: "bg-green-500/20 text-green-400",
  skipped: "bg-red-500/20 text-red-400",
};

const RESPONSE_COLORS: Record<string, string> = {
  strong_positive_response: "text-green-400 bg-green-500/10",
  mild_positive_response: "text-green-300 bg-green-500/10",
  stable_response: "text-foreground/60 bg-gray-500/10",
  fatigue_limited_response: "text-amber-400 bg-amber-500/10",
  negative_response: "text-red-400 bg-red-500/10",
  insufficient_checkpoint_data: "text-foreground/40 bg-gray-500/10",
};

export function AdaptiveExecutionPanel({ execution, analysis, onStart, onCompleteDay, onClose, onRefresh }: AEPProps) {
  const [checkinDay, setCheckinDay] = useState<number | null>(null);
  const [form, setForm] = useState({ difficulty_rating: 5, clarity_rating: 5, fatigue_rating: 3, focus_quality: 6, notes: "", duration_minutes_actual: 10 });

  if (!execution) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-teal-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Plan Execution (V15)</div>
        <div className="text-foreground/50">No active execution. Start one from your adaptive plan.</div>
        <button onClick={onStart} className="px-3 py-1.5 rounded bg-teal-500/20 border border-teal-500/30 text-teal-300 hover:bg-teal-500/30">
          Start Execution
        </button>
      </div>
    );
  }

  const active = execution.status === "active";

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-teal-500/50">
      <div className="flex justify-between items-center">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Plan Execution (V15)</div>
        <span className={`px-2 py-0.5 rounded text-[8px] ${active ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-400"}`}>
          {active ? "Active" : "Completed"}
        </span>
      </div>

      <div className="text-foreground/60">{execution.plan_title}</div>
      <div className="text-foreground/40 text-[9px]">Focus: {execution.training_focus?.replace(/_/g, " ") || "—"}</div>

      <div className="grid grid-cols-4 gap-1 text-center">
        <div className="p-1 rounded bg-surface/30">
          <div className="text-foreground/30 text-[7px]">Done</div>
          <div className="text-green-400 text-[9px]">{execution.summary.completed_days}/{execution.summary.total_days}</div>
        </div>
        <div className="p-1 rounded bg-surface/30">
          <div className="text-foreground/30 text-[7px]">Skip</div>
          <div className="text-red-400 text-[9px]">{execution.summary.skipped_days}</div>
        </div>
        <div className="p-1 rounded bg-surface/30">
          <div className="text-foreground/30 text-[7px]">Left</div>
          <div className="text-foreground/50 text-[9px]">{execution.summary.pending_days}</div>
        </div>
        <div className="p-1 rounded bg-surface/30">
          <div className="text-foreground/30 text-[7px]">Adh.</div>
          <div className="text-foreground/50 text-[9px]">{(execution.summary.adherence_rate * 100).toFixed(0)}%</div>
        </div>
      </div>

      <div className="space-y-1 max-h-48 overflow-y-auto">
        {execution.days?.map((d) => (
          <div key={d.day} className={`flex items-center gap-2 p-1.5 rounded ${d.status === "completed" ? "bg-green-500/5" : d.status === "skipped" ? "bg-red-500/5" : "bg-surface/30"}`}>
            <span className="text-foreground/30 w-5 text-[9px]">D{d.day}</span>
            <span className="text-foreground/60 flex-1 truncate text-[9px]">{d.planned_exercise?.title || "—"}</span>
            <span className={`px-1.5 py-0.5 rounded text-[7px] ${STATUS_COLORS[d.status] || ""}`}>
              {d.status}
            </span>
            {d.requires_calibration && (
              <span className={`text-[8px] ${d.checkpoint_pid != null ? "text-cyan-400" : "text-foreground/30"}`}>
                {d.checkpoint_pid != null ? `PID:${d.checkpoint_pid.toFixed(2)}` : "C"}
              </span>
            )}
            {active && d.status === "pending" && (
              <button onClick={() => setCheckinDay(d.day)} className="px-2 py-0.5 rounded text-[8px] bg-accent/20 border border-accent/30 text-accent-glow hover:bg-accent/30">
                +
              </button>
            )}
          </div>
        ))}
      </div>

      {checkinDay && (
        <div className="p-3 rounded bg-surface/50 space-y-2">
          <div className="text-foreground/40 text-[9px]">Day {checkinDay} Check-in</div>
          <div className="grid grid-cols-2 gap-2">
            {(["difficulty_rating", "clarity_rating", "fatigue_rating", "focus_quality"] as const).map((k) => (
              <div key={k} className="text-foreground/50 text-[8px]">
                <label>{k.replace(/_/g, " ")} ({form[k as keyof typeof form]})</label>
                <input type="range" min="1" max="10" value={form[k as keyof typeof form]} onChange={(e) => setForm({ ...form, [k]: Number(e.target.value) })}
                  className="w-full h-1 bg-surface-border rounded" />
              </div>
            ))}
            <div className="col-span-2 text-foreground/50 text-[8px]">
              <label>Duration (min): {form.duration_minutes_actual}</label>
              <input type="range" min="1" max="30" value={form.duration_minutes_actual} onChange={(e) => setForm({ ...form, duration_minutes_actual: Number(e.target.value) })}
                className="w-full h-1 bg-surface-border rounded" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => { onCompleteDay(checkinDay, { ...form, completed: true }); setCheckinDay(null); }}
              className="px-3 py-1 rounded bg-green-500/20 border border-green-500/30 text-green-400 hover:bg-green-500/30 text-[9px]">
              Complete
            </button>
            <button onClick={() => { onCompleteDay(checkinDay, { completed: false }); setCheckinDay(null); }}
              className="px-3 py-1 rounded bg-red-500/20 border border-red-500/30 text-red-400 hover:bg-red-500/30 text-[9px]">
              Skip
            </button>
            <button onClick={() => setCheckinDay(null)} className="px-3 py-1 rounded bg-surface border border-surface-border text-foreground/50 text-[9px]">
              Cancel
            </button>
          </div>
        </div>
      )}

      {analysis && (
        <div className="p-2 rounded bg-surface/30 space-y-1">
          <div className="text-foreground/50 text-[9px]">Response: <span className={`px-1.5 py-0.5 rounded text-[8px] ${RESPONSE_COLORS[analysis.response_category] || ""}`}>{analysis.response_category?.replace(/_/g, " ") || "—"}</span></div>
          {analysis.pid_checkpoint_analysis?.meaningful_improvement !== undefined && (
            <div className="text-foreground/40 text-[9px]">
              PID Change: {analysis.pid_checkpoint_analysis?.baseline_to_final_change?.toFixed(3)} |
              Meaningful: {analysis.pid_checkpoint_analysis?.meaningful_improvement ? "Yes" : "No"}
            </div>
          )}
          {analysis.subjective_metrics && (
            <div className="text-foreground/30 text-[8px]">
              Fatigue: {analysis.subjective_metrics.avg_fatigue} · Focus: {analysis.subjective_metrics.avg_focus_quality} · Clarity: {analysis.subjective_metrics.avg_clarity}
            </div>
          )}
          <div className="text-foreground/40 text-[8px] leading-relaxed">{analysis.interpretation?.slice(0, 200)}</div>
        </div>
      )}

      <div className="flex gap-2">
        {active && (
          <button onClick={onClose} className="px-3 py-1.5 rounded bg-amber-500/20 border border-amber-500/30 text-amber-300 hover:bg-amber-500/30">
            Close Execution
          </button>
        )}
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>

      <div className="text-foreground/20 text-[7px]">{execution.scientific_boundary}</div>
    </div>
  );
}
