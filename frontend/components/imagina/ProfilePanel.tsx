"use client";

interface ProfileProps {
  profile: {
    session_count: number; total_steps: number;
    mean_iqi: number; mean_pid: number;
    best_iqi: number; best_pid: number;
    iqi_trend_slope: number; pid_trend_slope: number;
    fatigue_trend_slope: number;
    optimal_session_length_steps: number | null;
    fatigue_threshold_estimate: number | null;
    best_tasks: string[];
  } | null;
}

export function ProfilePanel({ profile }: ProfileProps) {
  if (!profile) return null;
  const trend = (v: number) => v > 0 ? "+" : "";
  return (
    <div className="glass panel-glow p-4 space-y-2 text-[10px] border-l-2 border-blue-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Personal Imagery Profile</div>
      <div className="grid grid-cols-2 gap-2">
        <div>Sessions: <span className="text-foreground font-mono">{profile.session_count}</span></div>
        <div>Steps: <span className="text-foreground font-mono">{profile.total_steps}</span></div>
        <div>Mean IQI: <span className="text-accent-glow font-mono">{profile.mean_iqi?.toFixed(3)}</span></div>
        <div>Mean PID: <span className="text-accent-glow font-mono">{profile.mean_pid?.toFixed(3)}</span></div>
        <div>Best IQI: <span className="text-green-400 font-mono">{profile.best_iqi?.toFixed(3)}</span></div>
        <div>Best PID: <span className="text-green-400 font-mono">{profile.best_pid?.toFixed(3)}</span></div>
      </div>
      <div className="text-foreground/50 space-y-0.5 mt-2">
        {profile.iqi_trend_slope !== 0 && (
          <div>IQI trend: {trend(profile.iqi_trend_slope)}{profile.iqi_trend_slope.toFixed(4)} {profile.iqi_trend_slope > 0 ? "↑" : "↓"}</div>
        )}
        {profile.fatigue_threshold_estimate && (
          <div>Fatigue limit: ~step {profile.fatigue_threshold_estimate}</div>
        )}
        {profile.optimal_session_length_steps && (
          <div>Optimal: ~{profile.optimal_session_length_steps} steps</div>
        )}
        {profile.best_tasks?.length > 0 && (
          <div>Best tasks: {profile.best_tasks.slice(0, 3).join(", ")}</div>
        )}
      </div>
    </div>
  );
}
