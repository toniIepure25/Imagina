"use client";

import { useState } from "react";

interface Task {
  task_id: string; title: string; category: string; difficulty: number;
  target_dimensions: string[]; prompt: string; instructions: string[];
  duration_seconds: number; scientific_boundary?: string;
}

interface ActiveSession {
  session_id: string; task_id: string; task_metadata: { title: string; category: string };
}

interface ITBProps {
  tasks: Task[] | null;
  categories: string[];
  activeSession: ActiveSession | null;
  onStartTask: (taskId: string) => void;
  onSubmitRating: (sessionId: string, payload: Record<string, number>) => void;
  onComplete: (sessionId: string) => void;
  onRefresh: () => void;
}

const DIFF_COLORS: Record<number, string> = {
  1: "text-signal", 2: "text-signal", 3: "text-lock", 4: "text-lock", 5: "text-danger",
};

export function ImageryTaskBatteryPanel({ tasks, categories, activeSession, onStartTask, onSubmitRating, onComplete, onRefresh }: ITBProps) {
  const [selCat, setSelCat] = useState("");
  const [form, setForm] = useState<Record<string, number>>({
    vividness: 5, stability: 5, color_control: 5, spatial_control: 5,
    detail: 5, motion: 5, emotion: 5, multisensory: 5, meta_control: 5,
    effort: 5, fatigue: 3, confidence: 7,
  });

  const filtered = tasks?.filter(t => !selCat || t.category === selCat) || [];

  if (!tasks) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[11px] border-l-2 border-emerald-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Imagery Task Battery (V19)</div>
        <div className="text-foreground/50">Loading tasks...</div>
      </div>
    );
  }

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[11px] border-l-2 border-emerald-500/50">
      <div className="flex justify-between items-center">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Imagery Tasks (V19)</div>
        <span className="text-foreground/30 text-[11px]">{tasks.length} tasks</span>
      </div>

      <select value={selCat} onChange={(e) => setSelCat(e.target.value)}
        className="px-2 py-1 rounded bg-surface border border-surface-border text-foreground/60 text-[11px] w-full">
        <option value="">All Categories</option>
        {categories?.map(c => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
      </select>

      {activeSession ? (
        <div className="p-3 rounded bg-signal/[0.06] space-y-2">
          <div className="text-signal text-[11px]">Active: {activeSession.task_metadata?.title}</div>
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            {["vividness", "stability", "color_control", "spatial_control", "detail", "motion"].map(k => (
              <div key={k}>
                <label className="text-foreground/40">{k.replace(/_/g, " ")} ({form[k]})</label>
                <input type="range" min="1" max="10" value={form[k]} onChange={e => setForm({...form, [k]: Number(e.target.value)})}
                  className="w-full h-1 bg-surface-border rounded" />
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={() => { onSubmitRating(activeSession.session_id, form); onComplete(activeSession.session_id); }}
              className="px-3 py-1 rounded bg-signal/10 border border-signal/25 text-signal hover:bg-signal/20 text-[11px]">
              Rate & Complete
            </button>
            <button onClick={onRefresh} className="px-3 py-1 rounded bg-surface border border-surface-border text-foreground/50 text-[11px]">Cancel</button>
          </div>
        </div>
      ) : (
        <div className="space-y-1 max-h-64 overflow-y-auto">
          {filtered.slice(0, 12).map(t => (
            <div key={t.task_id} className="flex gap-2 text-[11px] p-1.5 rounded bg-surface/30 items-center">
              <span className={DIFF_COLORS[t.difficulty] || "text-foreground/30"}>L{t.difficulty}</span>
              <span className="text-foreground/60 flex-1 truncate">{t.title}</span>
              <span className="text-foreground/30">{t.category?.replace(/_/g, " ")}</span>
              <button onClick={() => onStartTask(t.task_id)}
                className="px-2 py-0.5 rounded bg-accent/20 border border-accent/30 text-accent-glow hover:bg-accent/30">
                Start
              </button>
            </div>
          ))}
        </div>
      )}

      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
        Refresh Tasks
      </button>

      <div className="text-foreground/20 text-[11px]">{tasks[0]?.scientific_boundary}</div>
    </div>
  );
}
