"use client";

interface DimChange {
  first: number; latest: number; change: number;
}

interface Improvement {
  n_sessions: number; first_pid: number; latest_pid: number; absolute_change: number;
  relative_change_percent: number; trend: string; meaningful_change: boolean;
  rolling_last_3_mean_pid: number; rolling_first_3_mean_pid?: number;
  dimension_changes: Record<string, DimChange>;
  interpretation: string; scientific_boundary?: string;
}

interface IPProps {
  improvement: Improvement | null;
  onRefresh: () => void;
}

export function PidImprovementPanel({ improvement, onRefresh }: IPProps) {
  if (!improvement || improvement.n_sessions < 2) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-cyan-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">PID Improvement Tracker</div>
        <div className="text-foreground/50">
          {!improvement ? "No data yet." : `Only ${improvement.n_sessions} session(s). Complete at least 2 calibrations.`}
        </div>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>
    );
  }

  const trendColors: Record<string, string> = {
    improving: "text-green-400", slightly_improving: "text-green-300",
    stable: "text-foreground/60",
    declining: "text-red-400", slightly_declining: "text-amber-400",
    insufficient_data: "text-foreground/40",
  };

  const changeSign = improvement.absolute_change <= 0 ? "↓" : "↑";
  const changeColor = improvement.absolute_change <= 0 ? "text-green-400" : "text-amber-400";

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-cyan-500/50">
      <div className="flex justify-between items-center">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">PID Improvement Tracker</div>
        <span className={`px-2 py-0.5 rounded text-[8px] ${
          improvement.meaningful_change
            ? (improvement.absolute_change <= 0 ? "bg-green-500/20 text-green-400" : "bg-amber-500/20 text-amber-400")
            : "bg-gray-500/20 text-gray-400"
        }`}>
          {improvement.meaningful_change ? "Meaningful" : "Minimal"}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="p-2 rounded bg-surface/30 text-center">
          <div className="text-foreground/30 text-[8px]">First</div>
          <div className="text-foreground">{improvement.first_pid?.toFixed(3)}</div>
        </div>
        <div className="p-2 rounded bg-surface/30 text-center">
          <div className="text-foreground/30 text-[8px]">Latest</div>
          <div className="text-foreground">{improvement.latest_pid?.toFixed(3)}</div>
        </div>
        <div className="p-2 rounded bg-surface/30 text-center">
          <div className="text-foreground/30 text-[8px]">Change</div>
          <div className={changeColor}>
            {changeSign}{Math.abs(improvement.absolute_change).toFixed(3)} ({improvement.relative_change_percent}%)
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="text-foreground/50">Trend: <span className={trendColors[improvement.trend] || "text-foreground/60"}>{improvement.trend}</span></div>
        <div className="text-foreground/50">Sessions: <span className="text-foreground">{improvement.n_sessions}</span></div>
        <div className="text-foreground/50">Rolling Mean: <span className="text-foreground">{improvement.rolling_last_3_mean_pid?.toFixed(3)}</span></div>
        <div className="text-foreground/50">Change: <span className="changeColor">{improvement.absolute_change > 0 ? "+" : ""}{improvement.absolute_change.toFixed(3)}</span></div>
      </div>

      {improvement.dimension_changes && Object.keys(improvement.dimension_changes).length > 0 && (
        <div className="space-y-1">
          <div className="text-foreground/50 tracking-[0.05em]">Dimension Gaps</div>
          {Object.entries(improvement.dimension_changes).map(([key, d]) => {
            const dimChangeDir = d.change <= 0 ? "↓" : "↑";
            const dimColor = d.change <= 0 ? "text-green-400" : "text-amber-400";
            return (
              <div key={key} className="flex gap-2 text-[9px] p-1 rounded bg-surface/30">
                <span className="text-foreground/40 w-20">{key.replace(/_/g, " ")}</span>
                <span className="text-foreground/30">{d.first.toFixed(2)} → {d.latest.toFixed(2)}</span>
                <span className={dimColor}>{dimChangeDir}{Math.abs(d.change).toFixed(3)}</span>
              </div>
            );
          })}
        </div>
      )}

      <div className="text-foreground/40 text-[9px] leading-relaxed p-2 rounded bg-surface/20">
        {improvement.interpretation}
      </div>

      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
        Refresh
      </button>

      <div className="text-foreground/20 text-[7px]">{improvement.scientific_boundary}</div>
    </div>
  );
}
