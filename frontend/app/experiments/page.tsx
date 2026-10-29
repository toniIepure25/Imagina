"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import PageHeader from "@/components/platform/PageHeader";
import AsyncState from "@/components/platform/AsyncState";
import BoundaryNote from "@/components/platform/BoundaryNote";
import { apiFetch } from "@/lib/api";
import { pct } from "@/lib/formatters";
import type { ExperimentProgress, ExperimentProtocol, ExperimentRun, Session } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ExperimentsPage() {
  const [protocols, setProtocols] = useState<ExperimentProtocol[]>([]);
  const [run, setRun] = useState<ExperimentRun | null>(null);
  const [progress, setProgress] = useState<ExperimentProgress | null>(null);
  const [nextSession, setNextSession] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    apiFetch<ExperimentProtocol[]>("/api/experiments/protocols", { signal: controller.signal })
      .then((next) => {
        setProtocols(next);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (caught instanceof DOMException && caught.name === "AbortError") return;
        setError("Backend unavailable or experiment protocols could not be loaded.");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  const createRun = async (protocol: ExperimentProtocol) => {
    setCreating(protocol.protocol_id);
    setError(null);
    try {
      const created = await apiFetch<ExperimentRun>("/api/experiments/runs", {
        method: "POST",
        body: JSON.stringify({ protocol_id: protocol.protocol_id, participant_label: "local-demo" }),
      });
      setRun(created);
      setNextSession(null);
      setProgress(await apiFetch<ExperimentProgress>(`/api/experiments/runs/${created.run_id}/progress`));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The experiment run could not be created.");
    } finally {
      setCreating(null);
    }
  };

  const createNextSession = async () => {
    if (!run) return;
    setCreating("next");
    setError(null);
    try {
      const userId = window.localStorage.getItem("imagina_user_id");
      const query = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
      const session = await apiFetch<Session>(`/api/experiments/runs/${run.run_id}/next-session${query}`, { method: "POST" });
      setNextSession(session);
      setProgress(await apiFetch<ExperimentProgress>(`/api/experiments/runs/${run.run_id}/progress`));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The next session could not be created.");
    } finally {
      setCreating(null);
    }
  };

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-6xl space-y-5 px-4 py-8 md:px-6 lg:py-10">
        <PageHeader
          eyebrow="Research mode"
          title="Experiment protocols"
          description="Create a local run from an adaptive or fixed protocol, then open linked sessions in order. Metrics remain experimental proxies; catch trials are disclosed control feedback, not hidden decoding."
          actions={
            <Link
              href="/science"
              className="inline-flex min-h-10 items-center rounded-lg border border-white/12 px-4 text-sm text-foreground/60 hover:text-foreground"
            >
              Claim boundaries
            </Link>
          }
        />

        {error ? (
          <div role="alert" className="rounded-lg border border-danger/25 bg-danger/[0.05] px-4 py-3 text-sm text-danger/85">
            {error}
          </div>
        ) : null}

        {run ? (
          <section className="rounded-xl border border-accent/20 bg-accent/[0.05] p-4" aria-labelledby="active-run">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="mono-label text-accent-glow/70">Active run</p>
                <h2 id="active-run" className="mt-1 font-mono text-sm text-foreground/80">
                  {run.run_id}
                </h2>
                <p className="mt-1 text-xs text-foreground/45">
                  {run.catch_trials.length} catch-trial marker{run.catch_trials.length === 1 ? "" : "s"} · participant
                  label <span className="font-mono">local-demo</span>
                </p>
              </div>
              {progress ? (
                <div className="text-right">
                  <p className="font-mono text-lg text-accent-glow">
                    {progress.completed_count}/{progress.planned_count}
                  </p>
                  <p className="text-[11px] text-foreground/40">{pct(progress.percent_complete)} complete</p>
                </div>
              ) : null}
            </div>

            {progress?.protocol?.condition === "catch_trial_control" ? (
              <p className="mt-3 rounded-lg border border-lock/25 bg-lock/[0.07] px-3 py-2 text-xs leading-5 text-lock/85">
                Research-mode notice: some trials may hold feedback constant for validation. This is disclosed control
                feedback, not hidden dream decoding.
              </p>
            ) : null}

            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={createNextSession}
                disabled={creating === "next"}
                className="inline-flex min-h-10 items-center rounded-lg bg-accent px-4 text-sm font-medium text-white hover:bg-accent-glow hover:text-background disabled:opacity-50"
              >
                {creating === "next" ? "Creating…" : nextSession ? "Refresh next session" : "Create next session"}
              </button>
              {nextSession ? (
                <Link
                  href={`/session?experimentRunId=${run.run_id}&sessionId=${nextSession.session_id}`}
                  className="inline-flex min-h-10 items-center rounded-lg border border-signal/30 bg-signal/10 px-4 text-sm text-signal hover:bg-signal/15"
                >
                  Open linked session
                </Link>
              ) : null}
              <a
                href={`${API}/api/exports/experiment/${run.run_id}/summary.json`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex min-h-10 items-center rounded-lg border border-white/12 px-4 text-sm text-foreground/60 hover:text-foreground"
              >
                Export summary JSON
              </a>
            </div>

            {progress ? (
              <ol className="mt-4 grid gap-2 md:grid-cols-2">
                {progress.run.planned_sessions.map((step, index) => {
                  const sessionId = progress.run.session_ids[index];
                  const completed = sessionId && progress.run.completed_session_ids.includes(sessionId);
                  return (
                    <li key={index} className="rounded-lg border border-white/10 bg-black/15 p-3">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-xs font-medium text-foreground/75">
                          {String(index + 1).padStart(2, "0")} · {String(step.task_id || "corridor_simple").replaceAll("_", " ")}
                        </p>
                        <span className="rounded-full border border-white/10 px-2 py-0.5 text-[11px] text-foreground/45">
                          {completed ? "completed" : sessionId ? "created" : "planned"}
                        </span>
                      </div>
                      <p className="mt-1 text-[11px] text-foreground/40">
                        {String(step.scenario || "improving_user")}
                      </p>
                      {sessionId ? (
                        <Link href={`/reports/${sessionId}`} className="mt-2 inline-flex min-h-8 items-center text-xs text-accent-glow/80 hover:text-accent-glow">
                          View report →
                        </Link>
                      ) : null}
                    </li>
                  );
                })}
              </ol>
            ) : null}
          </section>
        ) : null}

        {loading ? (
          <AsyncState kind="loading" title="Loading protocols" body="Reading published protocol definitions from the local backend." />
        ) : protocols.length === 0 ? (
          <AsyncState
            kind="empty"
            title="No protocols available"
            body="The backend is reachable but returned no experiment protocols. This usually means the local database was not seeded."
          />
        ) : (
          <section aria-labelledby="protocols-title">
            <div className="flex flex-wrap items-end justify-between gap-2">
              <div>
                <p className="mono-label text-foreground/45">Available protocols</p>
                <h2 id="protocols-title" className="mt-1 text-xl font-semibold text-foreground">
                  Choose a condition
                </h2>
              </div>
              <p className="max-w-sm text-[11px] leading-5 text-foreground/35">
                Creating a run does not enroll a participant or start a session. Every run stays on this machine.
              </p>
            </div>
            <div className="mt-3 grid gap-4 lg:grid-cols-3">
              {protocols.map((protocol) => (
                <article key={protocol.protocol_id} className="flex flex-col rounded-xl border border-white/10 bg-white/[0.025] p-4">
                  <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-accent-glow/60">
                    {protocol.condition.replaceAll("_", " ")}
                  </p>
                  <h3 className="mt-2 text-lg font-semibold text-foreground/90">{protocol.name}</h3>
                  <p className="mt-2 flex-1 text-sm leading-6 text-foreground/55">{protocol.description}</p>
                  <dl className="mt-3 grid grid-cols-3 gap-2 border-t border-white/8 pt-3">
                    {[
                      ["Minutes", String(protocol.duration_minutes)],
                      ["Curriculum", protocol.curriculum_mode],
                      ["Catch rate", `${Math.round(protocol.catch_trial_rate * 100)}%`],
                    ].map(([term, value]) => (
                      <div key={term}>
                        <dt className="text-[11px] text-foreground/40">{term}</dt>
                        <dd className="mt-0.5 truncate text-xs text-foreground/65">{value}</dd>
                      </div>
                    ))}
                  </dl>
                  <button
                    type="button"
                    onClick={() => createRun(protocol)}
                    disabled={creating !== null}
                    className="mt-4 inline-flex min-h-10 items-center justify-center rounded-lg border border-accent/30 bg-accent/15 px-4 text-sm text-accent-glow hover:bg-accent/25 disabled:opacity-50"
                  >
                    {creating === protocol.protocol_id ? "Creating…" : "Create run"}
                  </button>
                </article>
              ))}
            </div>
          </section>
        )}

        <BoundaryNote>
          Experiment protocols organize local sessions; they do not establish efficacy, diagnosis, or a treatment
          effect. Catch-trial controls are disclosed in the active-run notice.
        </BoundaryNote>
      </div>
    </AppShell>
  );
}
