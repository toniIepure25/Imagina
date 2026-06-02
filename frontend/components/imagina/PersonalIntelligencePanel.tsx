"use client";

interface PIProps {
  profile: {
    n_analyzed_sessions: number; global_scores?: { overall_iqi_mean: number };
    strengths: string[]; weaknesses: string[]; reliability?: { confidence_level: string };
    scientific_boundary?: string;
  } | null;
  gaps: {
    primary_bottleneck: string; recommended_focus: string; explanation: string;
  } | null;
  recommendation: {
    title: string; reason: string; target_capability: string; confidence: string;
    expected_duration_days: number; difficulty_level: number;
  } | null;
  onRebuild: () => void; onGetRec: () => void; onReport: () => void;
}

export function PersonalIntelligencePanel({ profile, gaps, recommendation, onRebuild, onGetRec, onReport }: PIProps) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-emerald-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Personal Imagery Intelligence</div>

      {profile && profile.n_analyzed_sessions > 0 ? (
        <div className="grid grid-cols-2 gap-2">
          <div className="text-foreground/50">Sessions: <span className="text-foreground">{profile.n_analyzed_sessions}</span></div>
          <div className="text-foreground/50">IQI: <span className="text-accent-glow">{profile.global_scores?.overall_iqi_mean?.toFixed(3) || "?"}</span></div>
          <div className="text-foreground/50">Strengths: <span className="text-green-400">{profile.strengths?.join(", ") || "—"}</span></div>
          <div className="text-foreground/50">Growth: <span className="text-amber-400">{profile.weaknesses?.join(", ") || "—"}</span></div>
          <div className="col-span-2 text-foreground/30 text-[8px]">{profile.scientific_boundary}</div>
        </div>
      ) : (
        <div className="text-foreground/50">No profile data yet.</div>
      )}

      {gaps && (
        <div className="p-2 rounded bg-surface/30">
          <div className="text-foreground/50">Gap: <span className="text-amber-400">{gaps.primary_bottleneck}</span></div>
          <div className="text-foreground/40 text-[9px] mt-1">{gaps.explanation}</div>
        </div>
      )}

      {recommendation && (
        <div className="p-2 rounded bg-accent/5">
          <div className="text-foreground/50">Next: <span className="text-accent-glow">{recommendation.title}</span></div>
          <div className="text-foreground/40 text-[9px] mt-1">{recommendation.reason}</div>
          <div className="text-foreground/30 text-[8px] mt-1">Confidence: {recommendation.confidence} · ~{recommendation.expected_duration_days} days</div>
        </div>
      )}

      <div className="flex gap-2">
        <button onClick={onRebuild} className="px-3 py-1.5 rounded bg-accent/20 border border-accent/30 text-accent-glow hover:bg-accent/30">
          Build Profile
        </button>
        <button onClick={onGetRec} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Get Recommendation
        </button>
        <button onClick={onReport} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Report
        </button>
      </div>
    </div>
  );
}
