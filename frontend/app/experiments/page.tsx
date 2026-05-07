"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import Button from "@/components/common/Button";
import { apiFetch } from "@/lib/api";
import { pct } from "@/lib/formatters";
import type { ExperimentProgress, ExperimentProtocol, ExperimentRun, Session } from "@/lib/types";

export default function ExperimentsPage() {
  const [protocols, setProtocols] = useState<ExperimentProtocol[]>([]);
  const [run, setRun] = useState<ExperimentRun | null>(null);
  const [progress, setProgress] = useState<ExperimentProgress | null>(null);
  const [nextSession, setNextSession] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<ExperimentProtocol[]>("/api/experiments/protocols")
      .then(setProtocols)
      .catch(() => setError("Backend unavailable or experiment protocols could not be loaded."));
  }, []);

  const createRun = async (protocol: ExperimentProtocol) => {
    const created = await apiFetch<ExperimentRun>("/api/experiments/runs", {
      method: "POST",
      body: JSON.stringify({ protocol_id: protocol.protocol_id, participant_label: "local-demo" }),
    });
    setRun(created);
    setNextSession(null);
    setProgress(await apiFetch<ExperimentProgress>(`/api/experiments/runs/${created.run_id}/progress`));
  };

  const createNextSession = async () => {
    if (!run) return;
    const userId = window.localStorage.getItem("imagina_user_id");
    const query = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
    const session = await apiFetch<Session>(`/api/experiments/runs/${run.run_id}/next-session${query}`, { method: "POST" });
    setNextSession(session);
    setProgress(await apiFetch<ExperimentProgress>(`/api/experiments/runs/${run.run_id}/progress`));
  };

  return (
    <AppShell>
      <div className="flex-1 mx-auto w-full max-w-6xl p-6 lg:p-10 space-y-6">
        <div>
          <div className="text-[11px] uppercase tracking-[0.22em] text-accent-glow/70">Research Mode</div>
          <h1 className="mt-2 text-3xl font-bold glow-text">Experiment Protocols</h1>
          <p className="mt-3 max-w-3xl text-sm text-foreground/60">
            Research mode supports adaptive/fixed protocols and ethically disclosed control feedback. Metrics remain experimental proxies.
          </p>
        </div>
        {error && <div className="glass p-4 text-danger">{error}</div>}
        {run && (
          <div className="glass panel-glow p-5 text-sm text-foreground/70 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                Active run <span className="font-mono text-accent-glow">{run.run_id}</span>
                <span className="ml-2 text-foreground/45">with {run.catch_trials.length} catch-trial markers</span>
              </div>
              {progress && (
                <div className="font-mono text-accent-glow">{progress.completed_count}/{progress.planned_count} sessions | {pct(progress.percent_complete)}</div>
              )}
            </div>
            {progress?.protocol?.condition === "catch_trial_control" && (
              <div className="rounded-lg border border-yellow-400/25 bg-yellow-400/8 p-3 text-xs text-yellow-100/85">
                Research-mode notice: some trials may hold feedback constant for validation. This is disclosed control feedback, not hidden dream decoding.
              </div>
            )}
            <div className="flex flex-wrap gap-3">
              <Button size="sm" onClick={createNextSession}>
                {nextSession ? "Refresh Next Session" : "Create Next Session"}
              </Button>
              {nextSession && (
                <Link href={`/session?experimentRunId=${run.run_id}&sessionId=${nextSession.session_id}`}>
                  <Button size="sm" variant="secondary">Open Linked Session</Button>
                </Link>
              )}
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/exports/experiment/${run.run_id}/summary.json`} target="_blank" rel="noreferrer">
                <Button size="sm" variant="ghost">Export Summary JSON</Button>
              </a>
            </div>
            {progress && (
              <div className="grid gap-2 md:grid-cols-2">
                {progress.run.planned_sessions.map((step, index) => {
                  const sessionId = progress.run.session_ids[index];
                  const completed = sessionId && progress.run.completed_session_ids.includes(sessionId);
                  return (
                    <div key={index} className="rounded-lg border border-surface-border bg-surface/35 p-3 text-xs">
                      <div className="font-medium">Step {index + 1}: {String(step.task_id || "corridor_simple").replaceAll("_", " ")}</div>
                      <div className="mt-1 text-foreground/45">{String(step.scenario || "improving_user")} | {completed ? "completed" : sessionId ? "created" : "planned"}</div>
                      {sessionId && (
                        <Link href={`/reports/${sessionId}`} className="mt-2 inline-block text-accent-glow hover:underline">
                          View report
                        </Link>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
        <div className="grid gap-4 lg:grid-cols-3">
          {protocols.map((protocol) => (
            <div key={protocol.protocol_id} className="glass panel-glow p-5 space-y-3">
              <div className="text-[10px] uppercase tracking-[0.16em] text-foreground/40">{protocol.condition}</div>
              <h2 className="text-lg font-semibold text-accent-glow">{protocol.name}</h2>
              <p className="text-sm text-foreground/62">{protocol.description}</p>
              <div className="text-xs text-foreground/45">
                {protocol.duration_minutes} min | {protocol.curriculum_mode} | catch rate {Math.round(protocol.catch_trial_rate * 100)}%
              </div>
              <Button size="sm" variant="secondary" onClick={() => createRun(protocol)}>Create Run</Button>
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
