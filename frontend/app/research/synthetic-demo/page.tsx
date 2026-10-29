"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import BoundaryNote from "@/components/platform/BoundaryNote";
import EvidenceMark from "@/components/evidence/EvidenceMark";
import PageHeader from "@/components/platform/PageHeader";
import Panel from "@/components/platform/Panel";
import { apiFetch } from "@/lib/api";

interface RunStatus {
  run_id: string;
  study_id: string;
  status: string;
  sessions_completed: number;
  sessions_failed: number;
  total_sessions: number;
  export_ready: boolean;
  replay_verified: boolean;
  error: string | null;
}

const TERMINAL = new Set(["completed", "completed_with_failures", "failed", "aborted"]);

function emptyRun(runId: string, studyId: string): RunStatus {
  return {
    run_id: runId,
    study_id: studyId,
    status: "accepted",
    sessions_completed: 0,
    sessions_failed: 0,
    total_sessions: 0,
    export_ready: false,
    replay_verified: false,
    error: null,
  };
}

export default function SyntheticDemoPage() {
  const [studyId, setStudyId] = useState("synthetic-demo-001");
  const [participantCount, setParticipantCount] = useState(6);
  const [seed, setSeed] = useState(42);
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);

  const startStudy = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const created = await apiFetch<{ run_id: string }>("/api/synthetic-runtime/studies", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": `${studyId}-${Date.now()}`,
        },
        body: JSON.stringify({
          study_id: studyId,
          participant_count: participantCount,
          seed,
          trials_per_session: 5,
          windows_per_trial: 3,
        }),
      });
      setRunStatus(emptyRun(created.run_id, studyId));
      setPolling(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The synthetic study could not be started.");
    } finally {
      setLoading(false);
    }
  }, [participantCount, seed, studyId]);

  useEffect(() => {
    if (!polling || !runStatus?.run_id) return;
    let active = true;
    const poll = async () => {
      try {
        const data = await apiFetch<RunStatus>(`/api/synthetic-runtime/runs/${runStatus.run_id}`);
        if (!active) return;
        setRunStatus(data);
        if (TERMINAL.has(data.status)) setPolling(false);
      } catch {
        // Polling is best-effort; the local server may still be starting the run.
      }
    };
    const interval = window.setInterval(poll, 2000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [polling, runStatus?.run_id]);

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-4xl space-y-5 px-4 py-8 md:px-6 lg:py-10">
        <PageHeader
          eyebrow="Synthetic runtime"
          title="Three-condition engineering run"
          description="A deterministic synthetic study that exercises the runtime, export, and replay pipeline. It is not human-subject, behavioural, or neuroscientific evidence."
          meta={
            <span className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/35">
              synthetic · not human data
              <EvidenceMark evidenceId="synthetic.estimate" />
            </span>
          }
          actions={
            <Link
              href="/research"
              className="inline-flex h-11 items-center rounded-lg border border-surface-border px-3 text-[11px] text-foreground/60 hover:bg-white/[0.04] hover:text-foreground"
            >
              Research platform
            </Link>
          }
        />

        {!runStatus ? (
          <Panel className="p-5">
            <h2 className="text-base font-semibold">Configure the synthetic run</h2>
            <p className="mt-1 text-sm leading-6 text-foreground/50">
              Participants here are simulated agents generated from a seed. No human data is collected.
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <label className="block">
                <span className="mono-label text-foreground/45">Study ID</span>
                <input
                  value={studyId}
                  onChange={(event) => setStudyId(event.target.value)}
                  className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none focus:border-signal/40"
                />
              </label>
              <label className="block">
                <span className="mono-label text-foreground/45">Synthetic participants</span>
                <input
                  type="number"
                  min={2}
                  max={60}
                  value={participantCount}
                  onChange={(event) => setParticipantCount(Number(event.target.value))}
                  className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none focus:border-signal/40"
                />
              </label>
              <label className="block">
                <span className="mono-label text-foreground/45">Seed</span>
                <input
                  type="number"
                  value={seed}
                  onChange={(event) => setSeed(Number(event.target.value))}
                  className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 font-mono text-sm outline-none focus:border-signal/40"
                />
              </label>
            </div>
            <button
              type="button"
              onClick={startStudy}
              disabled={loading}
              className="mt-4 inline-flex min-h-11 items-center rounded-lg border border-signal/35 bg-signal/[0.09] px-4 text-sm font-medium text-signal hover:bg-signal/[0.14] disabled:opacity-40"
            >
              {loading ? "Starting…" : "Start synthetic run"}
            </button>
            {error ? (
              <p role="alert" className="mt-3 rounded-lg border border-danger/30 bg-danger/[0.05] px-3 py-2 text-sm text-danger">
                {error}
              </p>
            ) : null}
          </Panel>
        ) : (
          <Panel className="p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold">Run progress</h2>
                <p className="mt-1 font-mono text-[11px] text-foreground/35">
                  {runStatus.study_id} · {runStatus.run_id.slice(0, 8)}
                </p>
              </div>
              <span
                className={`rounded-full border px-2.5 py-1 font-mono text-[11px] ${
                  TERMINAL.has(runStatus.status)
                    ? runStatus.status === "completed"
                      ? "border-signal/30 bg-signal/[0.07] text-signal"
                      : "border-lock/30 bg-lock/[0.07] text-lock"
                    : "border-accent/30 bg-accent/[0.07] text-accent-glow"
                }`}
              >
                {runStatus.status}
              </span>
            </div>

            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
              {[
                ["Sessions", `${runStatus.sessions_completed}/${runStatus.total_sessions || "—"}`],
                ["Failed", String(runStatus.sessions_failed)],
                ["Export", runStatus.export_ready ? "ready" : "pending"],
                ["Replay", runStatus.replay_verified ? "verified" : "pending"],
                ["Polling", polling ? "active" : "stopped"],
              ].map(([term, value]) => (
                <div key={term} className="rounded-lg border border-surface-border bg-white/[0.025] p-3">
                  <dt className="mono-label text-foreground/35">{term}</dt>
                  <dd className="mt-1 font-mono text-foreground/75">{value}</dd>
                </div>
              ))}
            </dl>

            {runStatus.status === "completed" ? (
              <p className="mt-4 rounded-lg border border-signal/30 bg-signal/[0.05] p-3 text-sm text-signal">
                Synthetic run completed. Completion is an engineering check, not evidence of efficacy.
              </p>
            ) : null}

            {runStatus.error ? (
              <p role="alert" className="mt-4 rounded-lg border border-danger/30 bg-danger/[0.05] p-3 text-sm text-danger">
                {runStatus.error}
              </p>
            ) : null}

            <button
              type="button"
              onClick={() => {
                setRunStatus(null);
                setError(null);
                setPolling(false);
              }}
              className="mt-4 inline-flex min-h-11 items-center rounded-lg border border-surface-border px-4 text-sm text-foreground/60 hover:bg-white/[0.04]"
            >
              Start a new run
            </button>
          </Panel>
        )}

        <BoundaryNote>
          Synthetic participants are generated by code. Their results test the runtime and analysis plumbing only;
          they cannot establish a human effect, clinical benefit, or a neural mechanism.
        </BoundaryNote>
      </div>
    </AppShell>
  );
}
