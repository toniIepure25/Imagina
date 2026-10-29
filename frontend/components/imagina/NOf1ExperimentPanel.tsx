"use client";

import { useState } from "react";

interface ExperimentDay {
  day: number; condition: string; exercise: { title: string; duration_minutes: number };
  requires_calibration: boolean; status: string;
  checkin: Record<string, unknown> | null;
  checkpoint_pid: number | null;
}

interface Experiment {
  experiment_id: string; design_type: string; status: string;
  started_at: string; blocks: Array<{ block_id: number; condition: string }>;
  days: ExperimentDay[];
  summary?: { completed_days: number; total_days: number; adherence_rate: number };
  scientific_boundary?: string;
}

interface ExpAnalysis {
  primary_result: { direction: string; pid_delta_advantage: number; confidence_level: string };
  condition_metrics: Record<string, { days: number; avg_fatigue: number; avg_focus_quality: number }>;
}

interface NEPProps {
  experiment: Experiment | null;
  analysis: ExpAnalysis | null;
  onDesign: (design: string) => void;
  onStart: () => void;
  onCompleteDay: (day: number, payload: Record<string, unknown>) => void;
  onClose: () => void;
  onRefresh: () => void;
}

const CONDITION_COLORS: Record<string, string> = {
  baseline: "bg-accent/10 text-accent-glow",
  optimized: "bg-rose-500/20 text-rose-400",
  low_intensity: "bg-signal/10 text-signal",
  normal_intensity: "bg-lock/10 text-lock",
  high_intensity: "bg-danger/10 text-danger",
};

export function NOf1ExperimentPanel({ experiment, analysis, onDesign, onStart, onCompleteDay, onClose, onRefresh }: NEPProps) {
  const [designChoice, setDesignChoice] = useState("AB");
  const [checkinDay, setCheckinDay] = useState<number | null>(null);
  const [form, setForm] = useState({
    difficulty_rating: 5, clarity_rating: 5, fatigue_rating: 3,
    focus_quality: 6, confidence_rating: 7, notes: "", duration_minutes_actual: 10,
  });

  if (!experiment && !analysis) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[11px] border-l-2 border-orange-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">N-of-1 Experiments (V17)</div>
        <div className="text-foreground/50">Design a controlled personal experiment to compare plans.</div>
        <div className="flex gap-2 items-center">
          <select value={designChoice} onChange={(e) => setDesignChoice(e.target.value)}
            className="px-2 py-1 rounded bg-surface border border-surface-border text-foreground/60 text-[11px]">
            <option value="AB">AB</option>
            <option value="BA">BA</option>
            <option value="ABAB">ABAB</option>
            <option value="randomized_blocks">Randomized</option>
          </select>
          <button onClick={() => onDesign(designChoice)}
            className="px-3 py-1.5 rounded bg-orange-500/20 border border-orange-500/30 text-orange-300 hover:bg-orange-500/30">
            Design Experiment
          </button>
        </div>
      </div>
    );
  }

  const active = experiment?.status === "active";
  const designed = experiment?.status === "designed";

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[11px] border-l-2 border-orange-500/50">
      <div className="flex justify-between items-center">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">N-of-1 Experiment (V17)</div>
        <span className={`px-2 py-0.5 rounded text-[11px] ${
          active ? "bg-signal/10 text-signal" : designed ? "bg-lock/10 text-lock" : "bg-foreground/10 text-foreground/50"
        }`}>
          {experiment?.status || "—"}
        </span>
      </div>

      <div className="text-foreground/60">Design: {experiment?.design_type}</div>

      {active || (experiment?.days && experiment?.days.length > 0) ? (
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {experiment?.days?.map((d) => (
            <div key={d.day} className={`flex items-center gap-2 p-1.5 rounded ${
              d.status === "completed" ? "bg-signal/[0.04]" : d.status === "skipped" ? "bg-danger/[0.04]" : "bg-surface/30"
            }`}>
              <span className="text-foreground/30 w-5 text-[11px]">D{d.day}</span>
              <span className={`px-1 py-0.5 rounded text-[11px] ${CONDITION_COLORS[d.condition] || "bg-foreground/10 text-foreground/50"}`}>
                {d.condition}
              </span>
              <span className="text-foreground/60 flex-1 truncate text-[11px]">{d.exercise?.title || "—"}</span>
              <span className={`text-[11px] ${d.status === "completed" ? "text-signal" : d.status === "skipped" ? "text-danger" : "text-foreground/30"}`}>
                {d.status}
              </span>
              {d.requires_calibration && (
                <span className={`text-[11px] ${d.checkpoint_pid != null ? "text-cyan-400" : "text-foreground/30"}`}>
                  {d.checkpoint_pid != null ? `PID:${d.checkpoint_pid.toFixed(2)}` : "C"}
                </span>
              )}
              {active && d.status === "pending" && (
                <button onClick={() => setCheckinDay(d.day)} className="px-2 py-0.5 rounded text-[11px] bg-accent/20 border border-accent/30 text-accent-glow hover:bg-accent/30">
                  +
                </button>
              )}
            </div>
          ))}
        </div>
      ) : null}

      {checkinDay && (
        <div className="p-3 rounded bg-surface/50 space-y-2">
          <div className="text-foreground/40 text-[11px]">Day {checkinDay} Check-in</div>
          <div className="grid grid-cols-2 gap-2">
            {(["difficulty_rating", "clarity_rating", "fatigue_rating", "focus_quality", "confidence_rating"] as const).map((k) => (
              <div key={k} className="text-foreground/50 text-[11px]">
                <label>{k.replace(/_/g, " ")} ({form[k]})</label>
                <input type="range" min="1" max="10" value={form[k]} onChange={(e) => setForm({ ...form, [k]: Number(e.target.value) })}
                  className="w-full h-1 bg-surface-border rounded" />
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={() => { onCompleteDay(checkinDay, { ...form, completed: true }); setCheckinDay(null); }}
              className="px-3 py-1 rounded bg-signal/10 border border-green-500/30 text-signal hover:bg-green-500/30 text-[11px]">
              Complete
            </button>
            <button onClick={() => { onCompleteDay(checkinDay, { completed: false }); setCheckinDay(null); }}
              className="px-3 py-1 rounded bg-danger/10 border border-danger/25 text-danger hover:bg-danger/20 text-[11px]">
              Skip
            </button>
            <button onClick={() => setCheckinDay(null)} className="px-3 py-1 rounded bg-surface border border-surface-border text-foreground/50 text-[11px]">
              Cancel
            </button>
          </div>
        </div>
      )}

      {analysis && (
        <div className="p-2 rounded bg-surface/30 space-y-1">
          <div className="text-foreground/50 text-[11px]">
            Direction: <span className="text-orange-300">{analysis.primary_result?.direction}</span>
            <span className="text-foreground/30 ml-1">(conf: {analysis.primary_result?.confidence_level})</span>
          </div>
          {analysis.condition_metrics && (
            <div className="text-foreground/30 text-[11px]">
              Baseline: {analysis.condition_metrics.baseline?.days}d | Optimized: {analysis.condition_metrics.optimized?.days}d
            </div>
          )}
        </div>
      )}

      <div className="flex gap-2">
        {designed && (
          <button onClick={onStart} className="px-3 py-1.5 rounded bg-signal/10 border border-green-500/30 text-signal hover:bg-green-500/30">
            Start Experiment
          </button>
        )}
        {active && (
          <button onClick={onClose} className="px-3 py-1.5 rounded bg-lock/10 border border-amber-500/30 text-lock hover:bg-amber-500/30">
            Close Experiment
          </button>
        )}
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>

      <div className="text-foreground/20 text-[11px]">{experiment?.scientific_boundary}</div>
    </div>
  );
}
