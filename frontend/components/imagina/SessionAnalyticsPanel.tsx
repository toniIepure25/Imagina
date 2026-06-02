"use client";

interface AnalyticsProps {
  analytics: {
    session_id: string; n_steps: number;
    mean_iqi: number; mean_pid: number;
    best_iqi: number; best_step: number;
    iqi_slope: number; pid_slope: number; fatigue_slope: number;
    interpretation: string;
  } | null;
}

export function SessionAnalyticsPanel({ analytics }: AnalyticsProps) {
  if (!analytics || analytics.n_steps === 0) return null;
  const fmt = (v: number) => (v > 0 ? "+" : "") + v.toFixed(4);
  return (
    <div className="glass panel-glow p-4 space-y-2 text-[10px] border-l-2 border-green-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Session Analytics</div>
      <div className="grid grid-cols-2 gap-2">
        <div>Steps: <span className="font-mono">{analytics.n_steps}</span></div>
        <div>Best IQI: <span className="font-mono">{analytics.best_iqi?.toFixed(3)}</span></div>
        <div>IQI slope: <span className="font-mono">{fmt(analytics.iqi_slope)}</span></div>
        <div>PID slope: <span className="font-mono">{fmt(analytics.pid_slope)}</span></div>
        <div>Fatigue slope: <span className="font-mono">{fmt(analytics.fatigue_slope)}</span></div>
        <div>Best step: <span className="font-mono">#{analytics.best_step}</span></div>
      </div>
      <div className="text-foreground/50 mt-1">{analytics.interpretation}</div>
    </div>
  );
}
