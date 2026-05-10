"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import Button from "@/components/common/Button";
import { apiFetch } from "@/lib/api";
import { fixed, pct } from "@/lib/formatters";
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
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const userId = window.localStorage.getItem("imagina_user_id");
    if (!userId) return;
    apiFetch<ImageryProfile>(`/api/users/${userId}/profile`).then(setProfile).catch(() => {
      window.localStorage.removeItem("imagina_user_id");
    });
    apiFetch<LongitudinalReport>(`/api/users/${userId}/longitudinal-report`).then(setReport).catch(() => setReport(null));
  }, []);

  const createProfile = async () => {
    setLoading(true);
    try {
      const created = await apiFetch<ImageryProfile>("/api/users/local", {
        method: "POST",
        body: JSON.stringify({ display_name: "Local Research User" }),
      });
      window.localStorage.setItem("imagina_user_id", created.user_id);
      setProfile(created);
      setReport(await apiFetch<LongitudinalReport>(`/api/users/${created.user_id}/longitudinal-report`));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <div className="flex-1 mx-auto w-full max-w-6xl p-6 lg:p-10 space-y-6">
        <div>
          <div className="text-[11px] uppercase tracking-[0.22em] text-accent-glow/70">Local-only Profile</div>
          <h1 className="mt-2 text-3xl font-bold glow-text">Imagery Progress</h1>
          <p className="mt-3 max-w-3xl text-sm text-foreground/60">
            Profiles are stored locally and summarize experimental proxy metrics across completed sessions.
          </p>
        </div>

        {!profile ? (
          <div className="glass panel-glow p-6">
            <p className="mb-4 text-sm text-foreground/65">Create an anonymous local profile to track progress and recommendations.</p>
            <Button onClick={createProfile} disabled={loading}>{loading ? "Creating..." : "Create Local Profile"}</Button>
          </div>
        ) : (
          <>
            <div className="grid gap-3 md:grid-cols-4">
              {[
                ["Sessions", String(profile.total_sessions)],
                ["Total Minutes", String(profile.total_minutes)],
                ["Best IQI", pct(profile.best_iqi)],
                ["Best PID", fixed(profile.best_pid)],
                ["Max Level", String(profile.max_level_reached)],
                ["Fatigue Sensitivity", pct(profile.fatigue_sensitivity)],
                ["Optimal Difficulty", pct(profile.optimal_difficulty_estimate)],
                ["Avg IQI", pct(profile.average_iqi)],
                ["Avg PID", fixed(profile.average_pid)],
              ].map(([label, value]) => (
                <div key={label} className="glass panel-glow p-4">
                  <div className="text-[10px] uppercase tracking-[0.16em] text-foreground/40">{label}</div>
                  <div className="mt-2 font-mono text-2xl font-bold text-accent-glow">{value}</div>
                </div>
              ))}
            </div>
            <div className="glass panel-glow p-5">
              <h2 className="font-semibold">Recommended next session</h2>
              <p className="mt-2 text-sm text-foreground/62">
                {report
                  ? `Start near level ${report.recommendation.recommended_starting_level} with ${report.recommendation.recommended_task.replaceAll("_", " ")} for about ${report.recommendation.recommended_duration_minutes} minutes.`
                  : `Start near level ${Math.max(1, profile.max_level_reached)} with ${profile.preferred_task_type.replaceAll("_", " ")}.`}
              </p>
              {report && <p className="mt-2 text-sm text-foreground/50">{report.recommendation.rationale}</p>}
              <p className="mt-2 text-xs text-foreground/42">
                This profile id is remembered in this browser and attached to new local sessions.
              </p>
            </div>
            {report && (
              <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
                <div className="glass panel-glow p-5">
                  <h2 className="font-semibold">Longitudinal trends</h2>
                  <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
                    <div><div className="text-foreground/40">IQI slope</div><div className="font-mono text-accent-glow">{fixed(report.trends.iqi_slope, 4)}</div></div>
                    <div><div className="text-foreground/40">PID slope</div><div className="font-mono text-accent-glow">{fixed(report.trends.pid_slope, 4)}</div></div>
                    <div><div className="text-foreground/40">Fatigue slope</div><div className="font-mono text-accent-glow">{fixed(report.trends.fatigue_slope, 4)}</div></div>
                  </div>
                </div>
                <div className="glass panel-glow p-5">
                  <h2 className="font-semibold">Recent sessions</h2>
                  <div className="mt-3 divide-y divide-surface-border">
                    {report.recent_sessions.length === 0 && <div className="py-3 text-sm text-foreground/45">No completed sessions yet.</div>}
                    {report.recent_sessions.slice().reverse().map((item) => {
                      const sessionId = String(item.session_id || "");
                      return (
                        <div key={sessionId} className="flex items-center justify-between gap-3 py-3 text-sm">
                          <div>
                            <div className="font-mono text-foreground/75">{sessionId.slice(0, 8) || "session"}</div>
                            <div className="text-xs text-foreground/45">IQI {pct(Number(item.average_iqi || 0))} | PID {fixed(Number(item.average_pid || 1))}</div>
                          </div>
                          {sessionId && <Link href={`/reports/${sessionId}`} className="text-xs text-accent-glow hover:underline">Report</Link>}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
