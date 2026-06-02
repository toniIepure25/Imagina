"use client";

export function PolicyLeaderboardPanel({ leaderboard, onBuild, onRefresh }: {
  leaderboard: { category_winners?: Record<string, string>; ranked_policies?: unknown[]; tradeoff_summary?: string } | null;
  onBuild: () => void; onRefresh: () => void;
}) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-amber-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Leaderboard (V41)</div>
      {leaderboard ? (
        <div className="space-y-1">
          <div className="text-foreground/50">Best: <span className="text-amber-400">{leaderboard.category_winners?.best_overall || "—"}</span></div>
          <div className="text-foreground/30 text-[8px]">{leaderboard.tradeoff_summary || ""}</div>
        </div>
      ) : (
        <div className="text-foreground/50">Build a leaderboard to see rankings.</div>
      )}
      <div className="flex gap-2">
        <button onClick={onBuild} className="px-3 py-1.5 rounded bg-amber-500/20 border border-amber-500/30 text-amber-300 hover:bg-amber-500/30">Build Leaderboard</button>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      </div>
    </div>
  );
}
