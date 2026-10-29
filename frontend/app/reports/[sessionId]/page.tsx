"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import AsyncState from "@/components/platform/AsyncState";
import BoundaryNote from "@/components/platform/BoundaryNote";
import EvidenceMark from "@/components/evidence/EvidenceMark";
import EvidenceRail from "@/components/evidence/EvidenceRail";
import VirtualList from "@/components/common/VirtualList";
import { apiFetch } from "@/lib/api";
import { pct, fixed, formatDuration } from "@/lib/formatters";
import type { SessionReport } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function interpretationChips(report: SessionReport) {
  const chips: string[] = [];
  if (report.summary.best_iqi > 0.65 && report.summary.best_pid < 0.45) chips.push("High IQI + low PID window");
  if (report.summary.fatigue_peak > 0.65) chips.push("Fatigue risk window");
  if (
    report.timeline.some(
      (event) =>
        event.event_type === "state_estimate" &&
        typeof event.payload.uncertainty === "number" &&
        event.payload.uncertainty > 0.65,
    )
  ) {
    chips.push("High uncertainty window");
  }
  if (report.summary.max_level_reached > 1) chips.push("Curriculum progression");
  return chips.length ? chips : ["Baseline practice session"];
}

function eventValue(payload: Record<string, unknown>) {
  if (typeof payload.iqi === "number") return `IQI ${pct(payload.iqi)}`;
  if (typeof payload.pid === "number") return `PID ${fixed(payload.pid)}`;
  if (typeof payload.current_level === "number") return `Level ${payload.current_level}`;
  if (typeof payload.uncertainty === "number") return `Uncertainty ${pct(payload.uncertainty)}`;
  if (typeof payload.fatigue === "number") return `Fatigue ${pct(payload.fatigue)}`;
  if (typeof payload.scene_clarity === "number") return `Clarity ${pct(payload.scene_clarity)}`;
  return "";
}

function downloadLink(sessionId: string, path: string, label: string) {
  return (
    <a
      key={path}
      href={`${API}${path}`}
      target="_blank"
      rel="noreferrer"
      className="inline-flex min-h-9 items-center rounded-lg border border-white/12 px-3 text-xs text-foreground/60 hover:border-white/20 hover:text-foreground"
    >
      {label}
    </a>
  );
}

export default function ReportPage() {
  const params = useParams();
  const sessionId = params.sessionId as string;
  const [report, setReport] = useState<SessionReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    apiFetch<SessionReport>(`/api/reports/${sessionId}`, { signal: controller.signal })
      .then(setReport)
      .catch((caught: unknown) => {
        if (caught instanceof DOMException && caught.name === "AbortError") return;
        setError(caught instanceof Error ? caught.message : "Report not found or session has no data.");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [sessionId]);

  return (
    <AppShell>
      <div className="dossier-sheet mx-auto w-full max-w-6xl space-y-5 px-4 py-8 md:px-6 lg:py-10">
        <header className="flex flex-wrap items-end justify-between gap-4 border-b border-surface-border pb-5">
          <div>
            <p className="mono-label text-accent-glow/70">Experimental proxy report</p>
            <h1 className="mt-2 font-display text-3xl tracking-tight text-foreground">Session dossier</h1>
            <p className="mt-1 font-mono text-[11px] text-foreground/40">session · {sessionId.slice(0, 18)}</p>
          </div>
          <div className="no-print flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => window.print()}
              className="inline-flex min-h-9 items-center rounded-lg bg-accent px-3 text-xs font-medium text-white hover:bg-accent-glow hover:text-background"
            >
              Print / save PDF
            </button>
            <Link
              href="/profile"
              className="inline-flex min-h-9 items-center rounded-lg border border-white/12 px-3 text-xs text-foreground/60 hover:text-foreground"
            >
              Local records
            </Link>
          </div>
        </header>

        {loading ? (
          <AsyncState kind="loading" title="Reading session evidence" body="Loading summary, timeline, and export links from local storage." />
        ) : error ? (
          <AsyncState
            kind="error"
            title="Report unavailable"
            body={`${error} The session may not exist, or the local backend may be offline.`}
            action={
              <Link href="/replay" className="inline-flex min-h-10 items-center rounded-lg border border-white/15 px-4 text-sm text-foreground/70 hover:text-foreground">
                Open replay
              </Link>
            }
          />
        ) : report ? (
          <>
            <div className="rounded-lg border border-lock/20 bg-lock/[0.045] px-4 py-3 text-xs leading-6 text-foreground/60">
              This report summarizes experimental proxy metrics. It does not represent decoded mental content, a
              composite imagery score, or clinical evaluation. Values are descriptive for this session only.
            </div>

            <section className="grid grid-cols-2 gap-2.5 md:grid-cols-3 lg:grid-cols-6" aria-label="Summary metrics">
              {[
                { label: "Avg IQI", value: pct(report.summary.average_iqi), sub: "higher proxy", color: "text-accent-glow", evidenceId: "iqi.proxy" },
                { label: "Best IQI", value: pct(report.summary.best_iqi), sub: "peak window", color: "text-signal", evidenceId: "iqi.proxy" },
                { label: "Avg PID", value: fixed(report.summary.average_pid), sub: "lower proxy", color: "text-lock", evidenceId: "pid.proxy" },
                { label: "Best PID", value: fixed(report.summary.best_pid), sub: "lowest window", color: "text-lock", evidenceId: "pid.proxy" },
                { label: "Max level", value: String(report.summary.max_level_reached), sub: "curriculum", color: "text-signal", evidenceId: "curriculum.level" },
                { label: "Fatigue peak", value: pct(report.summary.fatigue_peak), sub: "safety signal", color: "text-danger", evidenceId: "fatigue.proxy" },
              ].map((item) => (
                <div key={item.label} className="rounded-lg border border-white/10 bg-white/[0.025] p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-mono text-[11px] uppercase tracking-[0.1em] text-foreground/40">{item.label}</p>
                    <EvidenceMark evidenceId={item.evidenceId} />
                  </div>
                  <p className={`mt-2 font-mono text-2xl font-semibold ${item.color}`}>{item.value}</p>
                  <p className="mt-1 text-[11px] text-foreground/40">{item.sub}</p>
                </div>
              ))}
            </section>

            <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
              <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
                <h2 className="mono-label text-foreground/45">Interpretation</h2>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {interpretationChips(report).map((chip) => (
                    <span key={chip} className="rounded-full border border-accent/25 bg-accent/10 px-2.5 py-1 text-[11px] text-accent-glow">
                      {chip}
                    </span>
                  ))}
                </div>
                <p className="mt-3 text-sm leading-6 text-foreground/60">{report.summary.recommendation}</p>
                <dl className="mt-4 grid grid-cols-3 gap-3">
                  {[
                    ["Duration", formatDuration(report.summary.duration_seconds)],
                    ["Best streak", formatDuration(report.summary.best_stability_streak_seconds)],
                    ["Safety events", String(report.summary.safety_events_count)],
                  ].map(([term, value]) => (
                    <div key={term}>
                      <dt className="text-[11px] text-foreground/40">{term}</dt>
                      <dd className="mt-0.5 font-mono text-xs text-foreground/70">{value}</dd>
                    </div>
                  ))}
                </dl>
                {report.analysis ? (
                  <dl className="mt-4 grid grid-cols-3 gap-3 border-t border-white/8 pt-3">
                    {[
                      ["IQI slope", fixed(report.analysis.iqi_slope, 4)],
                      ["PID slope", fixed(report.analysis.pid_slope, 4)],
                      ["Uncertainty peak", pct(report.analysis.uncertainty_peak)],
                      ["Advances", String(report.analysis.level_advances)],
                      ["Regressions", String(report.analysis.level_regressions)],
                      ["Self reports", String(report.analysis.self_report_count)],
                    ].map(([term, value]) => (
                      <div key={term}>
                        <dt className="text-[11px] text-foreground/40">{term}</dt>
                        <dd className="mt-0.5 font-mono text-xs text-foreground/70">{value}</dd>
                      </div>
                    ))}
                  </dl>
                ) : null}
              </section>

              <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
                <h2 className="mono-label text-foreground/45">Session context</h2>
                <dl className="mt-2 grid grid-cols-2 gap-3">
                  {[
                    ["Task", report.metadata?.task_id || "unknown"],
                    ["Provider", report.metadata?.signal_provider_id || "unknown"],
                    ["Scenario", report.metadata?.scenario || "n/a"],
                    ["Experiment", report.metadata?.experiment_run_id ? report.metadata.experiment_run_id.slice(0, 8) : "none"],
                    ["Calibration", report.calibration ? pct(report.calibration.calibration_quality_score) : "missing"],
                    ["Warnings", String(report.calibration?.warnings.length || 0)],
                  ].map(([term, value]) => (
                    <div key={term}>
                      <dt className="text-[11px] text-foreground/40">{term}</dt>
                      <dd className="mt-0.5 break-all font-mono text-xs text-foreground/70">{value}</dd>
                    </div>
                  ))}
                </dl>
                {report.experiment ? (
                  <p className="mt-4 rounded-lg border border-accent/20 bg-accent/[0.06] px-3 py-2 text-[11px] leading-5 text-foreground/60">
                    Linked experiment progress: {report.experiment.completed_count}/{report.experiment.planned_count} sessions completed.
                    Completion is not evidence of efficacy.
                  </p>
                ) : null}
              </section>
            </div>

            <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
              <div className="flex flex-wrap items-end justify-between gap-2">
                <div>
                  <h2 className="mono-label text-foreground/45">Timeline</h2>
                  <p className="mt-1 text-xs text-foreground/40">
                    All {report.timeline.length} events · virtualized rows · local timestamps
                  </p>
                </div>
                <span className="font-mono text-[11px] text-foreground/35">{report.timeline.length} events</span>
              </div>
              <div className="mt-3">
                <div className="grid grid-cols-[minmax(0,1fr)_64px_minmax(0,1fr)] gap-2 border-b border-white/10 pb-1.5 font-mono text-[11px] uppercase tracking-[0.1em] text-foreground/40">
                  <span>Event</span>
                  <span>Window</span>
                  <span>Value</span>
                </div>
                <VirtualList
                  items={report.timeline}
                  rowHeight={34}
                  height={320}
                  ariaLabel="Session event timeline"
                  getKey={(event, index) => `${event.timestamp}-${index}`}
                  className="mt-1"
                  renderRow={(event) => (
                    <div className="grid h-full grid-cols-[minmax(0,1fr)_64px_minmax(0,1fr)] items-center gap-2 border-b border-white/[0.06] text-xs">
                      <span className="truncate text-foreground/70">{event.event_type}</span>
                      <span className="font-mono text-foreground/45">
                        {typeof event.payload.window_index === "number" ? event.payload.window_index : "—"}
                      </span>
                      <span className="truncate font-mono text-foreground/60">{eventValue(event.payload)}</span>
                    </div>
                  )}
                />
              </div>
            </section>

            <section className="no-print rounded-xl border border-white/10 bg-white/[0.025] p-4">
              <h2 className="mono-label text-foreground/45">Exports</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {downloadLink(sessionId, `/api/reports/${sessionId}`, "JSON report")}
                {downloadLink(sessionId, `/api/reports/${sessionId}/html`, "HTML report")}
                {downloadLink(sessionId, `/api/exports/session/${sessionId}/events.jsonl`, "Event log JSONL")}
                {downloadLink(sessionId, `/api/exports/session/${sessionId}/timeline.csv`, "Timeline CSV")}
                {downloadLink(sessionId, `/api/exports/session/${sessionId}/self_reports.csv`, "Self-report CSV")}
                {downloadLink(sessionId, `/api/exports/session/${sessionId}/summary.csv`, "Summary CSV")}
                {downloadLink(sessionId, "/api/exports/data_dictionary.md", "Data dictionary")}
                {report.metadata?.experiment_run_id
                  ? downloadLink(
                      sessionId,
                      `/api/exports/experiment/${report.metadata.experiment_run_id}/summary.json`,
                      "Experiment summary",
                    )
                  : null}
              </div>
            </section>

            <EvidenceRail className="no-print" />
            <BoundaryNote>
              PID and IQI are experimental composite proxies. This dossier is a local record of one session, not a
              clinical evaluation, diagnosis, or decoded mental content.
            </BoundaryNote>

            <div className="no-print flex flex-wrap gap-2">
              <Link
                href="/session"
                className="inline-flex min-h-10 items-center rounded-lg bg-accent px-4 text-sm font-medium text-white hover:bg-accent-glow hover:text-background"
              >
                Start another session
              </Link>
              <Link
                href={`/replay?sessionId=${sessionId}`}
                className="inline-flex min-h-10 items-center rounded-lg border border-white/12 px-4 text-sm text-foreground/65 hover:text-foreground"
              >
                Replay this session
              </Link>
            </div>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
