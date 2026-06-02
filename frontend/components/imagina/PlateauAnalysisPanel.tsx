"use client";

interface Plateau { type: string; dimension: string; severity: string; recommended_intervention: string; }
interface PlateauAnalysis { plateau_detected: boolean; plateaus: Plateau[]; overall_risk: string; recommended_next_action: string; scientific_boundary?: string; }

export function PlateauAnalysisPanel({ analysis, onRefresh }: { analysis: PlateauAnalysis | null; onRefresh: () => void }) {
  if (!analysis) return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-red-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Plateaus (V21)</div>
      <div className="text-foreground/50">Build a skill model first.</div>
      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
    </div>
  );
  const sevCol: Record<string,string> = { high: "text-red-400 bg-red-500/10", medium: "text-amber-400 bg-amber-500/10", low: "text-blue-400 bg-blue-500/10" };
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-red-500/50">
      <div className="flex justify-between"><div className="text-foreground/40 uppercase tracking-[0.1em]">Plateaus (V21)</div><span className={`px-2 py-0.5 rounded text-[8px] ${analysis.overall_risk === "high" ? "bg-red-500/20 text-red-400" : "bg-green-500/20 text-green-400"}`}>{analysis.overall_risk}</span></div>
      {analysis.plateaus?.slice(0, 3).map((p,i) => (
        <div key={i} className={`p-1.5 rounded ${sevCol[p.severity] || ""} text-[8px]`}>
          <div className="font-medium">{p.type?.replace(/_/g, " ")} · {p.dimension}</div>
          <div className="text-foreground/60">{p.recommended_intervention}</div>
        </div>
      ))}
      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      <div className="text-foreground/20 text-[7px]">{analysis.scientific_boundary}</div>
    </div>
  );
}
