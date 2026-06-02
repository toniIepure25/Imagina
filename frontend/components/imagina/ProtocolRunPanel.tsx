"use client";

interface ProtocolRun {
  run_id: string; protocol_name: string; status: string;
  session_ids: string[]; completed_steps: { day: number; task_id: string; session_id?: string }[];
  current_step_index: number;
}

interface ProtocolStep {
  day: number; task_id: string; difficulty: number;
}

export function ProtocolRunPanel({ run, nextStep, onAttach, onComplete, sessionId }:
  { run: ProtocolRun | null; nextStep: ProtocolStep | null;
    onAttach: () => void; onComplete: () => void; sessionId: string | null }) {
  if (!run) return null;
  return (
    <div className="glass panel-glow p-4 space-y-2 text-[10px] border-l-2 border-purple-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Protocol Run</div>
      <div className="font-mono">{run.protocol_name}</div>
      <div className="text-foreground/50">
        Status: <span className={run.status === "active" ? "text-green-400" : "text-amber-400"}>{run.status}</span> |
        Sessions: {run.session_ids.length} | Steps: {run.current_step_index}/{run.completed_steps.length}
      </div>
      {nextStep && (
        <div className="text-foreground/60">
          Next: <span className="text-accent-glow font-mono">{nextStep.task_id.replace(/_/g, " ")}</span>
          (day {nextStep.day}, difficulty {nextStep.difficulty})
        </div>
      )}
      <div className="flex gap-2">
        {sessionId && (
          <button onClick={onAttach}
                  className="px-3 py-1.5 rounded bg-accent/20 border border-accent/30 text-[10px] text-accent-glow hover:bg-accent/30">
            Attach Session
          </button>
        )}
        <button onClick={onComplete}
                className="px-3 py-1.5 rounded bg-surface border border-surface-border text-[10px] text-foreground/50 hover:bg-surface/50">
          Complete Run
        </button>
      </div>
    </div>
  );
}
