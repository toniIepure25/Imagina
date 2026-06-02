"use client";

interface TimelineEvent {
  timestamp: string; event_type: string; title: string; summary: string;
  metric_snapshot?: Record<string, unknown>;
}

interface Timeline {
  n_events: number; timeline: TimelineEvent[];
  scientific_boundary?: string;
}

interface ETPProps { timeline: Timeline | null; onRefresh: () => void; }

export function EvidenceTimelinePanel({ timeline, onRefresh }: ETPProps) {
  if (!timeline || timeline.n_events === 0) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-purple-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Evidence Timeline (V18)</div>
        <div className="text-foreground/50">No evidence events recorded yet.</div>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>
    );
  }

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-purple-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Evidence Timeline (V18)</div>
        <span className="text-foreground/30 text-[8px]">{timeline.n_events} events</span>
      </div>

      <div className="space-y-1 max-h-48 overflow-y-auto">
        {timeline.timeline.slice(-10).reverse().map((t, i) => (
          <div key={i} className="flex gap-2 text-[8px] p-1.5 rounded bg-surface/30">
            <span className="text-foreground/30 w-4 flex-shrink-0">
              {t.event_type?.includes("calibration") ? "C" :
               t.event_type?.includes("experiment") ? "E" :
               t.event_type?.includes("execut") ? "X" :
               t.event_type?.includes("plan") ? "P" : "•"}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-foreground/60 truncate">{t.title}</div>
              <div className="text-foreground/30 text-[7px]">{t.event_type?.replace(/_/g, " ")} · {t.summary?.slice(0, 50)}</div>
            </div>
            <span className="text-foreground/20 text-[7px] flex-shrink-0">{t.timestamp?.slice(0, 10)}</span>
          </div>
        ))}
      </div>

      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
        Refresh
      </button>

      <div className="text-foreground/20 text-[7px]">{timeline.scientific_boundary}</div>
    </div>
  );
}
