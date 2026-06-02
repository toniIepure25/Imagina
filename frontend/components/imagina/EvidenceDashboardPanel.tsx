"use client";

interface EvidenceModel {
  evidence_status: string; data_inventory: Record<string, number>;
  pid_summary: { first_pid?: number; latest_pid?: number; absolute_change?: number; trend: string };
  training_summary: { best_focus: string; fatigue_risk: string; adherence_risk: string };
  experiment_summary: { latest_direction: string; latest_evidence_score: number; latest_evidence_category: string };
  main_limitations: string[]; scientific_boundary?: string;
}

interface QualityAudit {
  quality_score: number; quality_category: string;
  passed_checks: string[]; warnings: string[]; critical_issues: string[];
}

interface Timeline {
  n_events: number; timeline: Array<{ timestamp: string; event_type: string; title: string; summary: string }>;
}

interface Recommendation {
  recommended_action: string; priority: string; why: string[]; next_steps: string[]; blocks_export: boolean;
}

interface EDPProps {
  evidence: EvidenceModel | null;
  quality: QualityAudit | null;
  timeline: Timeline | null;
  recommendation: Recommendation | null;
  onRefresh: () => void;
  onExport: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  insufficient: "bg-red-500/20 text-red-400",
  exploratory: "bg-amber-500/20 text-amber-400",
  promising_personal: "bg-emerald-500/20 text-emerald-400",
  strong_personal: "bg-green-500/20 text-green-400",
};

export function EvidenceDashboardPanel({ evidence, quality, timeline, recommendation, onRefresh, onExport }: EDPProps) {
  if (!evidence || evidence.evidence_status === "insufficient") {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-sky-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Evidence Dashboard (V18)</div>
        <div className="text-foreground/50">Insufficient data for an evidence dashboard. Complete calibrations and plans first.</div>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>
    );
  }

  const inv = evidence.data_inventory || {};
  const pid = evidence.pid_summary || {};
  const tr = evidence.training_summary || {};
  const exp = evidence.experiment_summary || {};

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-sky-500/50">
      <div className="flex justify-between items-center">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Evidence Dashboard (V18)</div>
        <span className={`px-2 py-0.5 rounded text-[8px] ${STATUS_COLORS[evidence.evidence_status] || "bg-gray-500/20 text-gray-400"}`}>
          {evidence.evidence_status}
        </span>
      </div>

      {quality && (
        <div className="flex items-center gap-2">
          <span className="text-foreground/50">Quality:</span>
          <span className="text-sky-300">{quality.quality_score}/100</span>
          <span className="text-foreground/30">({quality.quality_category})</span>
        </div>
      )}

      <div className="grid grid-cols-3 gap-1 text-center">
        {Object.entries({ Calib: inv.n_calibrations, Plans: inv.n_adaptive_plans, Execs: inv.n_executions, Exps: inv.n_n_of_1_experiments, "PID chg": pid.absolute_change, Trend: pid.trend }).map(([k, v]) => (
          <div key={k} className="p-1 rounded bg-surface/30">
            <div className="text-foreground/30 text-[7px]">{k}</div>
            <div className="text-foreground/60 text-[9px]">{typeof v === "number" ? (k === "PID chg" ? (v || 0).toFixed(2) : v) : String(v || "—")}</div>
          </div>
        ))}
      </div>

      {timeline && timeline.n_events > 0 && (
        <div className="space-y-1 max-h-24 overflow-y-auto">
          {timeline.timeline.slice(-5).reverse().map((t, i) => (
            <div key={i} className="flex gap-2 text-[8px] p-1 rounded bg-surface/30">
              <span className="text-foreground/40 w-16 truncate">{t.event_type?.replace(/_/g, " ")}</span>
              <span className="text-foreground/60 flex-1 truncate">{t.title?.slice(0, 30)}</span>
            </div>
          ))}
        </div>
      )}

      {quality?.critical_issues && quality.critical_issues.length > 0 && (
        <div className="text-red-400 text-[8px] p-1.5 rounded bg-red-500/10">
          Critical: {quality.critical_issues.join(", ")}
        </div>
      )}

      {recommendation && (
        <div className="p-2 rounded bg-sky-500/10 space-y-1">
          <div className="text-foreground/50 text-[9px]">
            Action: <span className="text-sky-300">{recommendation.recommended_action?.replace(/_/g, " ")}</span>
            <span className="text-foreground/30 ml-1">({recommendation.priority})</span>
          </div>
          {recommendation.why?.slice(0, 2).map((w, i) => (
            <div key={i} className="text-foreground/40 text-[8px]">{w}</div>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <button onClick={onExport} className="px-3 py-1.5 rounded bg-sky-500/20 border border-sky-500/30 text-sky-300 hover:bg-sky-500/30">
          Export Research Pack
        </button>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>

      <div className="text-foreground/20 text-[7px]">{evidence.scientific_boundary}</div>
    </div>
  );
}
