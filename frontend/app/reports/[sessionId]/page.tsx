"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import Card from "@/components/common/Card";
import Button from "@/components/common/Button";
import { apiFetch } from "@/lib/api";
import { pct, fixed, formatDuration } from "@/lib/formatters";
import type { SessionReport } from "@/lib/types";

function interpretationChips(report: SessionReport) {
  const chips: string[] = [];
  if (report.summary.best_iqi > 0.65 && report.summary.best_pid < 0.45) chips.push("Strong stabilization period");
  if (report.summary.fatigue_peak > 0.65) chips.push("Fatigue risk period");
  if (report.timeline.some((event) => event.event_type === "state_estimate" && typeof event.payload.uncertainty === "number" && event.payload.uncertainty > 0.65)) {
    chips.push("High uncertainty period");
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

export default function ReportPage() {
  const params = useParams();
  const sessionId = params.sessionId as string;
  const [report, setReport] = useState<SessionReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<SessionReport>(`/api/reports/${sessionId}`)
      .then(setReport)
      .catch(() => setError("Report not found or session has no data."));
  }, [sessionId]);

  return (
    <AppShell>
      <div className="flex-1 mx-auto w-full max-w-6xl p-6 lg:p-10 space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.22em] text-accent-glow/70">Experimental Proxy Report</div>
            <h1 className="mt-2 text-3xl font-bold glow-text">Session Report</h1>
          </div>
          <Link href="/" className="text-sm text-foreground/50 hover:text-foreground">Back to Home</Link>
        </div>

        {error && (
          <div className="glass p-6 text-danger">
            <div className="font-semibold">Report unavailable</div>
            <p className="mt-1 text-sm text-foreground/55">{error}</p>
          </div>
        )}

        {report && (
          <>
            <div className="glass panel-glow p-4 text-sm text-foreground/60 border-l-4 border-yellow-500/50">
              This report summarizes experimental proxy metrics. It does not represent decoded mental content or clinical evaluation.
            </div>

            <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-6">
              {[
                ["Avg IQI", pct(report.summary.average_iqi), "higher is better", "text-accent-glow"],
                ["Best IQI", pct(report.summary.best_iqi), "peak quality proxy", "text-cyan-200"],
                ["Avg PID", fixed(report.summary.average_pid), "lower is better", "text-yellow-400"],
                ["Best PID", fixed(report.summary.best_pid), "lowest distance proxy", "text-yellow-200"],
                ["Max Level", String(report.summary.max_level_reached), "curriculum", "text-green-300"],
                ["Fatigue Peak", pct(report.summary.fatigue_peak), "lower is better", "text-red-300"],
              ].map(([label, value, sub, color]) => (
                <div key={label} className="glass panel-glow p-4">
                  <div className="text-[10px] uppercase tracking-[0.16em] text-foreground/40">{label}</div>
                  <div className={`mt-2 font-mono text-2xl font-bold ${color}`}>{value}</div>
                  <div className="mt-1 text-[11px] text-foreground/42">{sub}</div>
                </div>
              ))}
            </div>

            <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
              <Card className="panel-glow">
                <h2 className="text-lg font-semibold mb-3">Interpretation</h2>
                <div className="flex flex-wrap gap-2">
                  {interpretationChips(report).map((chip) => (
                    <span key={chip} className="rounded-full border border-accent/25 bg-accent/10 px-3 py-1 text-xs text-accent-glow">
                      {chip}
                    </span>
                  ))}
                </div>
                <p className="mt-4 text-sm text-foreground/62">{report.summary.recommendation}</p>
                <div className="mt-4 grid grid-cols-3 gap-3 text-xs text-foreground/55">
                  <div><div className="text-foreground/35">Duration</div><div className="font-mono">{formatDuration(report.summary.duration_seconds)}</div></div>
                  <div><div className="text-foreground/35">Best Streak</div><div className="font-mono">{formatDuration(report.summary.best_stability_streak_seconds)}</div></div>
                  <div><div className="text-foreground/35">Safety Events</div><div className="font-mono">{report.summary.safety_events_count}</div></div>
                </div>
                {report.analysis && (
                  <div className="mt-4 grid grid-cols-3 gap-3 text-xs text-foreground/55">
                    <div><div className="text-foreground/35">IQI Slope</div><div className="font-mono">{fixed(report.analysis.iqi_slope, 4)}</div></div>
                    <div><div className="text-foreground/35">PID Slope</div><div className="font-mono">{fixed(report.analysis.pid_slope, 4)}</div></div>
                    <div><div className="text-foreground/35">Uncertainty Peak</div><div className="font-mono">{pct(report.analysis.uncertainty_peak)}</div></div>
                    <div><div className="text-foreground/35">Advances</div><div className="font-mono">{report.analysis.level_advances}</div></div>
                    <div><div className="text-foreground/35">Regressions</div><div className="font-mono">{report.analysis.level_regressions}</div></div>
                    <div><div className="text-foreground/35">Self Reports</div><div className="font-mono">{report.analysis.self_report_count}</div></div>
                  </div>
                )}
              </Card>

              <Card className="panel-glow">
                <h2 className="text-lg font-semibold mb-3">Session Context</h2>
                <div className="grid grid-cols-2 gap-3 text-xs text-foreground/55">
                  <div><div className="text-foreground/35">Task</div><div className="font-mono">{report.metadata?.task_id || "unknown"}</div></div>
                  <div><div className="text-foreground/35">Provider</div><div className="font-mono">{report.metadata?.signal_provider_id || "unknown"}</div></div>
                  <div><div className="text-foreground/35">Scenario</div><div className="font-mono">{report.metadata?.scenario || "n/a"}</div></div>
                  <div><div className="text-foreground/35">Experiment</div><div className="font-mono">{report.metadata?.experiment_run_id ? report.metadata.experiment_run_id.slice(0, 8) : "none"}</div></div>
                  <div><div className="text-foreground/35">Calibration</div><div className="font-mono">{report.calibration ? pct(report.calibration.calibration_quality_score) : "missing"}</div></div>
                  <div><div className="text-foreground/35">Warnings</div><div className="font-mono">{report.calibration?.warnings.length || 0}</div></div>
                </div>
                {report.experiment && (
                  <div className="mt-4 rounded-lg border border-accent/20 bg-accent/8 p-3 text-xs text-foreground/58">
                    Linked experiment progress: {report.experiment.completed_count}/{report.experiment.planned_count} sessions completed.
                  </div>
                )}
              </Card>
            </div>

            <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
              <Card className="panel-glow">
                <h2 className="text-lg font-semibold mb-3">Timeline</h2>
                <div className="max-h-80 overflow-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="text-foreground/45">
                      <tr>
                        <th className="py-2">Event</th>
                        <th className="py-2">Window</th>
                        <th className="py-2">Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-border">
                      {report.timeline.slice(-36).map((event, index) => {
                        const payload = event.payload;
                        return (
                          <tr key={`${event.timestamp}-${index}`}>
                            <td className="py-2 text-foreground/72">{event.event_type}</td>
                            <td className="py-2 font-mono text-foreground/50">
                              {typeof payload.window_index === "number" ? payload.window_index : "-"}
                            </td>
                            <td className="py-2 font-mono">{eventValue(payload)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>

            <div className="flex flex-wrap gap-3">
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/reports/${sessionId}`} target="_blank" rel="noreferrer">
                <Button variant="secondary" size="sm">Open JSON Report</Button>
              </a>
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/reports/${sessionId}/html`} target="_blank" rel="noreferrer">
                <Button variant="secondary" size="sm">Open HTML Report</Button>
              </a>
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/exports/session/${sessionId}/events.jsonl`} target="_blank" rel="noreferrer">
                <Button variant="secondary" size="sm">Event Log JSONL</Button>
              </a>
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/exports/session/${sessionId}/timeline.csv`} target="_blank" rel="noreferrer">
                <Button variant="secondary" size="sm">Timeline CSV</Button>
              </a>
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/exports/session/${sessionId}/self_reports.csv`} target="_blank" rel="noreferrer">
                <Button variant="secondary" size="sm">Self-report CSV</Button>
              </a>
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/exports/session/${sessionId}/summary.csv`} target="_blank" rel="noreferrer">
                <Button variant="secondary" size="sm">Summary CSV</Button>
              </a>
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/exports/data_dictionary.md`} target="_blank" rel="noreferrer">
                <Button variant="secondary" size="sm">Data Dictionary</Button>
              </a>
              {report.metadata?.experiment_run_id && (
                <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/exports/experiment/${report.metadata.experiment_run_id}/summary.json`} target="_blank" rel="noreferrer">
                  <Button variant="secondary" size="sm">Experiment Summary</Button>
                </a>
              )}
              <Link href="/session">
                <Button variant="ghost" size="sm">Start Another Session</Button>
              </Link>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
