"use client";

interface Rec {
  type: string; priority: string; message: string; reason: string;
  next_task_id?: string;
}

interface RecsProps { recommendations: Rec[] | null; }

export function RecommendationPanel({ recommendations }: RecsProps) {
  if (!recommendations || recommendations.length === 0) return null;
  const colors: Record<string, string> = {
    high: "bg-red-400", medium: "bg-amber-400", low: "bg-blue-400",
  };
  return (
    <div className="glass panel-glow p-4 space-y-2 text-[10px] border-l-2 border-amber-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Adaptive Recommendations</div>
      {recommendations.slice(0, 4).map((r, i) => (
        <div key={i} className="flex gap-2 items-start">
          <span className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${colors[r.priority] || "bg-gray-400"}`} />
          <div>
            <span className="text-foreground/60">{r.message}</span>
            <div className="text-foreground/30 mt-0.5">{r.reason}</div>
          </div>
        </div>
      ))}
      <div className="text-foreground/25 text-[8px] mt-2">Experimental proxy — not medical advice.</div>
    </div>
  );
}
