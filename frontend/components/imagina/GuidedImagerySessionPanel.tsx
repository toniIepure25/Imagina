"use client";

import { useState } from "react";

interface GuidedSession {
  session_id: string; task_id: string; task_metadata: { title: string; category: string };
  current_phase: string; status: string; micro_checkins: unknown[];
  scientific_boundary?: string;
}

interface Proxies {
  iqi_proxy: number; pid_proxy: number; stability_proxy: number;
  fatigue_risk: string; safety_state: string; adaptation_reason: string;
  modality_disclaimer?: string;
}

interface Feedback {
  feedback_type: string; guidance_text: string; scene_feedback: Record<string, number>;
  why: string[]; safety_state: string;
}

interface GSPProps {
  session: GuidedSession | null;
  proxies: Proxies | null;
  feedback: Feedback | null;
  onStart: (taskId: string) => void;
  onAdvance: () => void;
  onCheckin: (payload: Record<string, number>) => void;
  onPause: () => void;
  onResume: () => void;
  onComplete: () => void;
  onRefresh: () => void;
}

const PHASE_LABELS: Record<string, string> = {
  preparation: "Prep", grounding: "Ground", image_generation: "Generate",
  stabilization: "Stabilize", deepening: "Deepen", manipulation: "Manipulate",
  micro_checkin: "Check-in", adaptive_feedback: "Feedback", integration: "Integrate",
  completion: "Complete",
};

export function GuidedImagerySessionPanel({ session, proxies, feedback, onStart, onAdvance, onCheckin, onPause, onResume, onComplete, onRefresh }: GSPProps) {
  const [taskId, setTaskId] = useState("");
  const [form, setForm] = useState({ vividness: 5, stability: 5, effort: 5, fatigue: 3, confidence: 7, discomfort: 1 });

  if (!session) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[11px] border-l-2 border-cyan-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Guided Session (V20)</div>
        <input value={taskId} onChange={e => setTaskId(e.target.value)} placeholder="task_id" className="px-2 py-1 rounded bg-surface border border-surface-border text-foreground/60 text-[11px] w-full" />
        <button onClick={() => onStart(taskId || "red_circle_vividness")}
          className="px-3 py-1.5 rounded bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/30">
          Start Guided Session
        </button>
      </div>
    );
  }

  const active = session.status === "active";

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[11px] border-l-2 border-cyan-500/50">
      <div className="flex justify-between items-center">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Guided Session (V20)</div>
        <span className={`px-2 py-0.5 rounded text-[11px] ${active ? "bg-signal/10 text-signal" : "bg-foreground/10 text-foreground/50"}`}>
          {session.status}
        </span>
      </div>

      <div className="text-foreground/60">{session.task_metadata?.title}</div>
      <div className="flex items-center gap-2 text-[11px]">
        <span className="text-cyan-400">{PHASE_LABELS[session.current_phase] || session.current_phase}</span>
        <div className="flex-1 bg-surface-border rounded h-1">
          {[0,1,2,3,4,5,6,7,8,9].map(i => (
            <span key={i} className={`inline-block w-[10%] h-1 rounded ${i <= Object.keys(PHASE_LABELS).indexOf(session.current_phase) ? "bg-cyan-400" : "bg-transparent"}`} />
          ))}
        </div>
      </div>

      {feedback && (
        <div className="p-2 rounded bg-cyan-500/10 space-y-1 text-[11px]">
          <div className="text-cyan-300">{feedback.guidance_text}</div>
          <div className="text-foreground/30">Type: {feedback.feedback_type}</div>
        </div>
      )}

      {proxies && (
        <div className="grid grid-cols-3 gap-1 text-center text-[11px]">
          <div className="p-1 rounded bg-surface/30"><span className="text-foreground/30">IQI</span><br /><span className="text-cyan-400">{proxies.iqi_proxy?.toFixed(2)}</span></div>
          <div className="p-1 rounded bg-surface/30"><span className="text-foreground/30">PID</span><br /><span className="text-rose-400">{proxies.pid_proxy?.toFixed(2)}</span></div>
          <div className="p-1 rounded bg-surface/30"><span className="text-foreground/30">Stab</span><br /><span className="text-lock">{proxies.stability_proxy?.toFixed(2)}</span></div>
        </div>
      )}

      {active && (
        <div className="p-2 rounded bg-surface/50 space-y-2 text-[11px]">
          <div className="grid grid-cols-2 gap-1">
            {(["vividness", "stability", "effort", "fatigue", "confidence", "discomfort"] as const).map(k => (
              <div key={k}>
                <label className="text-foreground/40">{k} ({form[k]})</label>
                <input type="range" min="1" max="10" value={form[k]} onChange={e => setForm({...form, [k]: Number(e.target.value)})}
                  className="w-full h-1 bg-surface-border rounded" />
              </div>
            ))}
          </div>
          <button onClick={() => onCheckin(form)} className="w-full px-3 py-1 rounded bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/30 text-[11px]">
            Submit Check-in
          </button>
        </div>
      )}

      <div className="flex flex-wrap gap-1">
        {active && <button onClick={onAdvance} className="px-2 py-1 rounded bg-accent/20 border border-accent/30 text-accent-glow hover:bg-accent/30 text-[11px]">Advance</button>}
        {active && <button onClick={onPause} className="px-2 py-1 rounded bg-lock/10 border border-amber-500/30 text-lock hover:bg-amber-500/30 text-[11px]">Pause</button>}
        {session.status === "paused" && <button onClick={onResume} className="px-2 py-1 rounded bg-signal/10 border border-green-500/30 text-signal hover:bg-green-500/30 text-[11px]">Resume</button>}
        {active && <button onClick={onComplete} className="px-2 py-1 rounded bg-signal/10 border border-signal/25 text-signal hover:bg-signal/20 text-[11px]">Complete</button>}
        <button onClick={onRefresh} className="px-2 py-1 rounded bg-surface border border-surface-border text-foreground/50 text-[11px]">Refresh</button>
      </div>

      <div className="text-foreground/20 text-[11px]">{proxies?.modality_disclaimer || session.scientific_boundary}</div>
    </div>
  );
}
