"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { useImaginaSession } from "@/hooks/useImaginaSession";

const DreamCorridorScene = dynamic(() => import("@/components/scene/DreamCorridorScene"), { ssr: false });
import { DEFAULT_SCENE_PARAMS } from "@/lib/feedbackMapping";

function Metric({ label, value, unit = "", color = "accent" }: { label: string; value: number; unit?: string; color?: string }) {
  return (
    <div className="flex flex-col items-center p-2 rounded-lg bg-surface/30 border border-surface-border">
      <span className="text-[9px] uppercase tracking-wider text-foreground/40">{label}</span>
      <span className={`text-lg font-mono font-bold text-${color}-glow`}>
        {typeof value === "number" ? value.toFixed(3) : value}{unit}
      </span>
    </div>
  );
}

function SliderField({ label, value, onChange, min = 0, max = 10, step = 1, hint = "" }: {
  label: string; value: number; onChange: (v: number) => void; min?: number; max?: number; step?: number; hint?: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px]">
        <span className="text-foreground/60">{label}</span>
        <span className="text-foreground/40 font-mono">{value}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
             onChange={e => onChange(Number(e.target.value))}
             className="w-full h-1 bg-surface-border rounded-lg appearance-none cursor-pointer accent-accent" />
      {hint && <div className="text-[9px] text-foreground/30">{hint}</div>}
    </div>
  );
}

export default function ImaginaPage() {
  const s = useImaginaSession();
  const [sr, setSr] = useState({ vividness: 6, stability: 6, effort: 4, fatigue: 3, comfort: 7 });
  const srKeys = ["vividness", "stability", "effort", "fatigue", "comfort"] as const;
  type SrKey = typeof srKeys[number];
  const getSr = (k: string): number => sr[k as SrKey] ?? 5;

  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      {/* Hero */}
      <div className="border-b border-surface-border bg-surface/20 px-6 py-8">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-accent-glow/60">IMAGINA Lab</div>
              <h1 className="text-3xl font-bold mt-1">Mental Imagery Training</h1>
              <p className="text-sm text-foreground/40 mt-2 max-w-lg">
                Closed-loop guided imagery with experimental IQI/PID proxy metrics.
                Adaptive curriculum, procedural scene feedback, local-first session tracking.
              </p>
            </div>
            <div className="text-right space-y-2">
              <div className={`text-[10px] px-2 py-1 rounded-full ${s.sessionId ? "bg-green-500/20 text-green-300" : "bg-amber-500/20 text-amber-300"}`}>
                {s.sessionId ? `Session active` : "No session"}
              </div>
              {s.error && <div className="text-[10px] text-red-400">{s.error}</div>}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-6 grid gap-6 lg:grid-cols-3">
        {/* LEFT: Controls */}
        <div className="lg:col-span-1 space-y-4">
          {/* Setup */}
          <div className="glass panel-glow p-4 border-l-2 border-accent space-y-3">
            <div className="text-[10px] uppercase tracking-[0.16em] text-foreground/40">Session Setup</div>

            {!s.sessionId ? (
              <>
                <select value={s.demoProfile} onChange={e => s.setDemoProfile(e.target.value)}
                        className="w-full bg-surface border border-surface-border rounded p-2 text-xs text-foreground">
                  {s.DEMO_PROFILES.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <button onClick={s.start} disabled={s.loading}
                        className="w-full px-4 py-2 rounded bg-accent text-background text-sm font-medium hover:opacity-90 disabled:opacity-50">
                  {s.loading ? "Starting..." : "Start Session"}
                </button>
              </>
            ) : (
              <div className="text-[10px] text-foreground/50 font-mono break-all">{s.sessionId}</div>
            )}

            {s.sessionId && (
              <>
                <select value={s.taskId} onChange={e => s.setTaskId(e.target.value)}
                        className="w-full bg-surface border border-surface-border rounded p-2 text-xs text-foreground">
                  {s.TASKS.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
                </select>
                <button onClick={s.startT} disabled={s.loading}
                        className="w-full px-4 py-2 rounded bg-surface border border-surface-border text-xs text-foreground hover:bg-surface/50">
                  Start Task
                </button>
              </>
            )}
          </div>

          {/* Self-report */}
          {s.sessionId && (
            <div className="glass panel-glow p-4 border-l-2 border-accent space-y-3">
              <div className="text-[10px] uppercase tracking-[0.16em] text-foreground/40">Self-Report</div>
              {[
                ["vividness", "How clear is the image?"],
                ["stability", "How stable does it remain?"],
                ["effort", "How much effort are you using?"],
                ["fatigue", "Mental tiredness"],
                ["comfort", "Subjective comfort/safety"],
              ].map(([key, hint]) => (
                <SliderField key={key} label={key} hint={hint}
                             value={getSr(key)} onChange={v => setSr(p => ({ ...p, [key]: v }))} />
              ))}
              <button onClick={async () => { await s.submitSR(sr); await s.step(); }}
                      disabled={s.loading}
                      className="w-full px-4 py-2 rounded bg-accent text-background text-sm font-medium hover:opacity-90 disabled:opacity-50">
                {s.loading ? "Running..." : "Submit & Run Step"}
              </button>
            </div>
          )}

          {/* Scientific Boundaries */}
          <div className="p-3 rounded border border-amber-500/20 bg-amber-500/5">
            <div className="text-[9px] uppercase tracking-[0.1em] text-amber-400/70">Scientific Boundaries</div>
            <div className="mt-2 text-[9px] text-foreground/40 space-y-1">
              <div className="text-green-400/60">✓ Guided imagery practice</div>
              <div className="text-green-400/60">✓ Proxy state estimation</div>
              <div className="text-green-400/60">✓ Local-first session tracking</div>
              <div className="text-red-400/60 mt-1">✗ Mind reading / dream decoding</div>
              <div className="text-red-400/60">✗ Clinical therapy / diagnosis</div>
              <div className="text-red-400/60">✗ Production BCI</div>
            </div>
          </div>
        </div>

        {/* CENTER: Metrics */}
        <div className="lg:col-span-1 space-y-4">
          {/* IQI + PID */}
          <div className="glass panel-glow p-4 grid grid-cols-2 gap-3">
            <Metric label="IQI" value={s.lastStep?.iqi_score ?? 0} />
            <Metric label="PID" value={s.lastStep?.pid_score ?? 0} />
            <div className="col-span-2 text-[9px] text-foreground/30 text-center">
              {s.lastStep?.iqi_interpretation || "Run a step to compute metrics"}
            </div>
          </div>

          {/* State */}
          {s.lastStep?.state && (
            <div className="glass panel-glow p-4 space-y-2">
              <div className="text-[10px] uppercase tracking-[0.16em] text-foreground/40">State Estimate</div>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(s.lastStep.state).map(([k, v]) => (
                  <div key={k} className="text-[10px]">
                    <span className="text-foreground/40">{k.replace(/_/g, " ")}</span>
                    <div className="w-full h-1 bg-surface-border rounded-full mt-1">
                      <div className="h-1 bg-accent rounded-full" style={{ width: `${((Number(v)) * 100).toFixed(0)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Curriculum + Safety */}
          {s.lastStep && (
            <div className="glass panel-glow p-4 space-y-3">
              <div>
                <span className="text-[10px] uppercase tracking-[0.16em] text-foreground/40">Curriculum</span>
                <div className={`text-sm font-mono mt-1 ${s.lastStep.curriculum_action === "advance" ? "text-green-400" : s.lastStep.curriculum_action === "stop" ? "text-red-400" : "text-amber-300"}`}>
                  {s.lastStep.curriculum_action}
                </div>
                <div className="text-[9px] text-foreground/50">{s.lastStep.curriculum_message}</div>
              </div>
              <div>
                <span className="text-[10px] uppercase tracking-[0.16em] text-foreground/40">Safety</span>
                <div className={`text-sm font-mono mt-1 ${s.lastStep.safety_action !== "continue" ? "text-red-400" : "text-green-400"}`}>
                  {s.lastStep.safety_action}
                </div>
                <div className="text-[9px] text-foreground/50">{s.lastStep.safety_message}</div>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT: Scene + Profile */}
        <div className="lg:col-span-1 space-y-4">
          {/* Scene */}
          <div className="glass panel-glow overflow-hidden rounded-lg" style={{ height: 300 }}>
            <div className="absolute top-2 left-2 z-10 text-[8px] text-foreground/30">Simulated proxy feedback</div>
            <DreamCorridorScene
              params={{
                ...DEFAULT_SCENE_PARAMS,
                clarity: s.lastStep?.scene_params?.clarity ?? DEFAULT_SCENE_PARAMS.clarity,
                blur: s.lastStep?.scene_params?.visual_noise ?? DEFAULT_SCENE_PARAMS.blur,
                lightStability: s.lastStep?.scene_params?.saturation ?? DEFAULT_SCENE_PARAMS.lightStability,
                textureDetail: s.lastStep?.scene_params?.object_detail ?? DEFAULT_SCENE_PARAMS.textureDetail,
                particleStability: s.lastStep?.scene_params?.motion_speed ?? DEFAULT_SCENE_PARAMS.particleStability,
                doorComplexity: s.lastStep?.scene_params?.scene_complexity ?? DEFAULT_SCENE_PARAMS.doorComplexity,
                fogDensity: 1 - (s.lastStep?.scene_params?.clarity ?? 0.5),
                colorSaturation: s.lastStep?.scene_params?.saturation ?? DEFAULT_SCENE_PARAMS.colorSaturation,
                breathingCueStrength: s.lastStep?.scene_params?.breathing_cue_intensity ?? 0.5,
              }}
            />
          </div>

          {/* Summary + controls */}
          {s.sessionId && (
            <div className="space-y-2">
              <button onClick={s.refresh} className="w-full px-3 py-2 rounded bg-surface border border-surface-border text-[10px] text-foreground/50 hover:bg-surface/50">
                Refresh Summary
              </button>
              <button onClick={() => { s.updateProfile(); s.loadAnalytics(); }} className="w-full px-3 py-2 rounded bg-accent/20 border border-accent/30 text-[10px] text-accent-glow hover:bg-accent/30">
                Update Profile & Analytics
              </button>
              <button onClick={s.reset} className="w-full px-3 py-2 rounded text-[10px] text-red-400/70 hover:bg-red-500/5">
                Reset Session
              </button>
            </div>
          )}

          {s.summary && (
            <div className="glass panel-glow p-4 space-y-2 text-[10px]">
              <div className="text-foreground/40 uppercase tracking-[0.1em]">Summary</div>
              <div>Steps: {s.summary.total_steps} | IQI: {s.summary.mean_iqi} | PID: {s.summary.mean_pid}</div>
              <div className="text-foreground/30">{s.summary.disclaimer}</div>
            </div>
          )}

          {/* Profile */}
          {s.profile && (
            <div className="glass panel-glow p-4 space-y-2 text-[10px] border-l-2 border-blue-500/50">
              <div className="text-foreground/40 uppercase tracking-[0.1em]">Profile</div>
              <div className="grid grid-cols-2 gap-2">
                <div>Sessions: {s.profile.session_count}</div>
                <div>Steps: {s.profile.total_steps}</div>
                <div>Mean IQI: {s.profile.mean_iqi?.toFixed(3)}</div>
                <div>Mean PID: {s.profile.mean_pid?.toFixed(3)}</div>
                <div>Best IQI: {s.profile.best_iqi?.toFixed(3)}</div>
                <div>Best PID: {s.profile.best_pid?.toFixed(3)}</div>
              </div>
              {s.profile.iqi_trend_slope !== 0 && (
                <div className="text-foreground/50">
                  IQI trend: {s.profile.iqi_trend_slope > 0 ? "+" : ""}{s.profile.iqi_trend_slope?.toFixed(3)}
                  {s.profile.iqi_trend_slope > 0 ? " ↑" : " ↓"}
                </div>
              )}
              {s.profile.optimal_session_length_steps && (
                <div className="text-foreground/50">Optimal length: ~{s.profile.optimal_session_length_steps} steps</div>
              )}
            </div>
          )}

          {/* Analytics */}
          {s.analytics && (
            <div className="glass panel-glow p-4 space-y-2 text-[10px] border-l-2 border-green-500/50">
              <div className="text-foreground/40 uppercase tracking-[0.1em]">Session Analytics</div>
              <div>Steps: {s.analytics.n_steps} | Best IQI: {s.analytics.best_iqi?.toFixed(3)} (step {s.analytics.best_step})</div>
              <div>IQI slope: {s.analytics.iqi_slope > 0 ? "+" : ""}{s.analytics.iqi_slope?.toFixed(4)}</div>
              <div>Fatigue slope: {s.analytics.fatigue_slope > 0 ? "+" : ""}{s.analytics.fatigue_slope?.toFixed(4)}</div>
              <div className="text-foreground/50">{s.analytics.interpretation}</div>
            </div>
          )}

          {/* Recommendations */}
          {s.profile?.recommendations && s.profile.recommendations.length > 0 && (
            <div className="glass panel-glow p-4 space-y-2 text-[10px] border-l-2 border-amber-500/50">
              <div className="text-foreground/40 uppercase tracking-[0.1em]">Recommendations</div>
              {s.profile.recommendations.slice(0, 4).map((r: { priority: string; message: string }, i: number) => (
                <div key={i} className="flex gap-2 items-start">
                  <span className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${r.priority === "high" ? "bg-red-400" : r.priority === "medium" ? "bg-amber-400" : "bg-blue-400"}`} />
                  <span className="text-foreground/60">{r.message}</span>
                </div>
              ))}
            </div>
          )}

          {/* Local-first privacy */}
          <div className="p-2 rounded border border-surface-border text-[8px] text-foreground/25 text-center">
            Local-first · Profiles stored locally · No upload · Experimental proxy metrics only
          </div>
        </div>
      </div>
    </main>
  );
}
