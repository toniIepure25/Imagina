"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import PageHeader from "@/components/platform/PageHeader";
import AsyncState from "@/components/platform/AsyncState";
import BoundaryNote from "@/components/platform/BoundaryNote";
import EvidenceMark from "@/components/evidence/EvidenceMark";
import EvidenceRail from "@/components/evidence/EvidenceRail";
import { apiFetch } from "@/lib/api";
import { fixed, pct } from "@/lib/formatters";
import { MEASUREMENT_BOUNDARY } from "@/lib/claims";
import type { ImageryProfile } from "@/lib/types";

interface LongitudinalReport {
  recommendation: {
    recommended_task: string;
    recommended_duration_minutes: number;
    recommended_starting_level: number;
    rationale: string;
  };
  trends: {
    iqi_slope: number;
    pid_slope: number;
    fatigue_slope: number;
    session_count: number;
  };
  recent_sessions: Record<string, unknown>[];
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<ImageryProfile | null>(null);
  const [report, setReport] = useState<LongitudinalReport | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const userId = window.localStorage.getItem("imagina_user_id");
    if (!userId) {
      const timer = window.setTimeout(() => setInitializing(false), 0);
      return () => {
        window.clearTimeout(timer);
        controller.abort();
      };
    }
    Promise.all([
      apiFetch<ImageryProfile>(`/api/users/${userId}/profile`, { signal: controller.signal }),
      apiFetch<LongitudinalReport>(`/api/users/${userId}/longitudinal-report`, { signal: controller.signal }).catch(() => null),
    ])
      .then(([nextProfile, nextReport]) => {
        setProfile(nextProfile);
        setReport(nextReport);
      })
      .catch((caught: unknown) => {
        if (caught instanceof DOMException && caught.name === "AbortError") return;
        window.localStorage.removeItem("imagina_user_id");
        setError("The saved local profile could not be loaded. It may have been deleted from the local database.");
      })
      .finally(() => setInitializing(false));
    return () => controller.abort();
  }, []);

  const createProfile = async () => {
    setLoading(true);
    setError(null);
    try {
      const created = await apiFetch<ImageryProfile>("/api/users/local", {
        method: "POST",
        body: JSON.stringify({ display_name: "Local Research User" }),
      });
      window.localStorage.setItem("imagina_user_id", created.user_id);
      setProfile(created);
      const nextReport = await apiFetch<LongitudinalReport>(`/api/users/${created.user_id}/longitudinal-report`).catch(
        () => null,
      );
      setReport(nextReport);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The local profile could not be created.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-6xl space-y-5 px-4 py-8 md:px-6 lg:py-10">
        <PageHeader
          eyebrow="Local-only profile"
          title="Imagery progress"
          description="A local record of completed sessions and experimental proxy metrics. This profile never leaves the machine and carries no account, email, or cloud identifier."
          meta={<span className="font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/35">no account · no telemetry</span>}
          actions={
            profile ? (
              <Link
                href="/session"
                className="inline-flex min-h-10 items-center rounded-lg bg-accent px-4 text-sm font-medium text-white hover:bg-accent-glow hover:text-background"
              >
                Start a session
              </Link>
            ) : undefined
          }
        />

        {initializing ? (
          <AsyncState kind="loading" title="Reading the local profile" body="Looking for a remembered profile id in this browser." />
        ) : error ? (
          <AsyncState
            kind="error"
            title="Profile unavailable"
            body={error}
            action={
              <button
                type="button"
                onClick={createProfile}
                disabled={loading}
                className="inline-flex min-h-10 items-center rounded-lg border border-white/15 px-4 text-sm text-foreground/70 hover:text-foreground"
              >
                {loading ? "Creating…" : "Create a new local profile"}
              </button>
            }
          />
        ) : !profile ? (
          <section className="rounded-xl border border-white/10 bg-white/[0.025] p-6">
            <p className="mono-label text-accent-glow/65">No profile yet</p>
            <h2 className="mt-2 text-xl font-semibold text-foreground">Start a local record</h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-foreground/55">
              Create an anonymous profile to remember recommendations and completed sessions across visits. The
              identifier is stored in this browser and in the local SQLite database only.
            </p>
            <button
              type="button"
              onClick={createProfile}
              disabled={loading}
              className="mt-5 inline-flex min-h-11 items-center rounded-lg bg-accent px-4 text-sm font-medium text-white hover:bg-accent-glow hover:text-background disabled:opacity-50"
            >
              {loading ? "Creating…" : "Create local profile"}
            </button>
          </section>
        ) : (
          <>
            <section className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5" aria-label="Profile summary">
              {[
                { label: "Sessions", value: String(profile.total_sessions) },
                { label: "Total minutes", value: String(profile.total_minutes) },
                { label: "Best IQI proxy", value: pct(profile.best_iqi), evidenceId: "iqi.proxy" },
                { label: "Best PID proxy", value: fixed(profile.best_pid), evidenceId: "pid.proxy" },
                { label: "Max level", value: String(profile.max_level_reached), evidenceId: "curriculum.level" },
                { label: "Average IQI", value: pct(profile.average_iqi), evidenceId: "iqi.proxy" },
                { label: "Average PID", value: fixed(profile.average_pid), evidenceId: "pid.proxy" },
                { label: "Fatigue sensitivity", value: pct(profile.fatigue_sensitivity), evidenceId: "fatigue.proxy" },
                { label: "Optimal difficulty", value: pct(profile.optimal_difficulty_estimate) },
                { label: "Preferred task", value: profile.preferred_task_type.replaceAll("_", " ") },
              ].map((item) => (
                <div key={item.label} className="rounded-lg border border-white/10 bg-white/[0.025] p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-mono text-[11px] uppercase tracking-[0.1em] text-foreground/40">{item.label}</p>
                    {item.evidenceId ? <EvidenceMark evidenceId={item.evidenceId} /> : null}
                  </div>
                  <p className="mt-1.5 truncate font-mono text-lg text-accent-glow">{item.value}</p>
                </div>
              ))}
            </section>

            <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
              <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
                <h2 className="mono-label text-foreground/45">Recommended next session</h2>
                <p className="mt-2 text-sm leading-6 text-foreground/65">
                  {report
                    ? `Start near level ${report.recommendation.recommended_starting_level} with ${report.recommendation.recommended_task.replaceAll("_", " ")} for about ${report.recommendation.recommended_duration_minutes} minutes.`
                    : `Start near level ${Math.max(1, profile.max_level_reached)} with ${profile.preferred_task_type.replaceAll("_", " ")}.`}
                </p>
                {report ? <p className="mt-2 text-xs leading-5 text-foreground/45">{report.recommendation.rationale}</p> : null}
                <p className="mt-3 border-t border-white/8 pt-3 text-[11px] leading-5 text-foreground/35">
                  The profile id is remembered in this browser and attached to new local sessions.
                </p>
              </section>

              <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
                <h2 className="mono-label text-foreground/45">Longitudinal trends</h2>
                {report ? (
                  <>
                    <dl className="mt-3 grid grid-cols-3 gap-3">
                      {[
                        ["IQI slope", fixed(report.trends.iqi_slope, 4)],
                        ["PID slope", fixed(report.trends.pid_slope, 4)],
                        ["Fatigue slope", fixed(report.trends.fatigue_slope, 4)],
                      ].map(([term, value]) => (
                        <div key={term}>
                          <dt className="text-[11px] text-foreground/40">{term}</dt>
                          <dd className="mt-0.5 font-mono text-sm text-accent-glow">{value}</dd>
                        </div>
                      ))}
                    </dl>
                    <p className="mt-3 text-xs leading-5 text-foreground/45">
                      Based on {report.trends.session_count} completed session{report.trends.session_count === 1 ? "" : "s"}. Slopes
                      are descriptive, not a forecast or a treatment effect.
                    </p>
                  </>
                ) : (
                  <p className="mt-3 text-xs leading-5 text-foreground/45">
                    Trends appear after the first completed session. One session cannot support a trend claim.
                  </p>
                )}
              </section>
            </div>

            <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
              <div className="flex flex-wrap items-end justify-between gap-2">
                <div>
                  <h2 className="mono-label text-foreground/45">Recent sessions</h2>
                  <p className="mt-1 text-xs text-foreground/40">Newest first · local records</p>
                </div>
                <Link href="/replay" className="text-xs text-accent-glow/75 hover:text-accent-glow">
                  Open replay →
                </Link>
              </div>
              {report && report.recent_sessions.length > 0 ? (
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full min-w-[560px] text-left text-xs">
                    <thead>
                      <tr className="border-b border-white/10 font-mono text-[11px] uppercase tracking-[0.1em] text-foreground/40">
                        <th className="py-2 pr-3 font-normal">Session</th>
                        <th className="py-2 pr-3 font-normal">IQI</th>
                        <th className="py-2 pr-3 font-normal">PID</th>
                        <th className="py-2 pr-3 font-normal">Level</th>
                        <th className="py-2 font-normal">Report</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.07]">
                      {report.recent_sessions
                        .slice()
                        .reverse()
                        .map((item) => {
                          const sessionId = String(item.session_id || "");
                          return (
                            <tr key={sessionId}>
                              <td className="py-2.5 pr-3 font-mono text-foreground/65">{sessionId.slice(0, 8) || "session"}</td>
                              <td className="py-2.5 pr-3 font-mono text-foreground/55">{pct(Number(item.average_iqi || 0))}</td>
                              <td className="py-2.5 pr-3 font-mono text-foreground/55">{fixed(Number(item.average_pid || 1))}</td>
                              <td className="py-2.5 pr-3 font-mono text-foreground/55">
                                {item.max_level != null ? String(item.max_level) : "—"}
                              </td>
                              <td className="py-2.5">
                                {sessionId ? (
                                  <Link href={`/reports/${sessionId}`} className="inline-flex min-h-8 items-center text-accent-glow/80 hover:text-accent-glow">
                                    Open dossier
                                  </Link>
                                ) : (
                                  "—"
                                )}
                              </td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="mt-3 rounded-lg border border-white/8 bg-black/15 px-3 py-4 text-xs text-foreground/45">
                  No completed sessions yet. Finish a session to populate this table.
                </p>
              )}
            </section>
          </>
        )}

        <EvidenceRail />
        <BoundaryNote>{MEASUREMENT_BOUNDARY}</BoundaryNote>
      </div>
    </AppShell>
  );
}
