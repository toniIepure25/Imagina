"use client";

interface QualityAudit {
  quality_score: number; quality_category: string;
  passed_checks: string[]; warnings: string[]; critical_issues: string[];
  recommended_next_actions: string[];
  scientific_boundary?: string;
}

interface EQPProps { quality: QualityAudit | null; onRefresh: () => void; }

const CAT_COLORS: Record<string, string> = {
  strong: "text-signal", good: "text-signal", usable: "text-lock", weak: "text-danger",
};

export function EvidenceQualityPanel({ quality, onRefresh }: EQPProps) {
  if (!quality) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[11px] border-l-2 border-blue-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Evidence Quality (V18)</div>
        <div className="text-foreground/50">No quality audit available yet.</div>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Refresh
        </button>
      </div>
    );
  }

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[11px] border-l-2 border-blue-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Evidence Quality (V18)</div>
        <span className={CAT_COLORS[quality.quality_category] || ""}>{quality.quality_score}/100</span>
      </div>

      {quality.passed_checks?.length > 0 && (
        <div className="space-y-1">
          <div className="text-foreground/50 text-[11px]">Passed Checks</div>
          {quality.passed_checks.map((c, i) => (
            <div key={i} className="text-signal text-[11px] p-1 rounded bg-signal/[0.04]">✓ {c.replace(/_/g, " ")}</div>
          ))}
        </div>
      )}

      {quality.warnings?.length > 0 && (
        <div className="space-y-1">
          <div className="text-foreground/50 text-[11px]">Warnings</div>
          {quality.warnings.map((w, i) => (
            <div key={i} className="text-lock text-[11px] p-1 rounded bg-amber-500/5">⚠ {w.replace(/_/g, " ")}</div>
          ))}
        </div>
      )}

      {quality.critical_issues?.length > 0 && (
        <div className="space-y-1">
          <div className="text-foreground/50 text-[11px]">Critical</div>
          {quality.critical_issues.map((c, i) => (
            <div key={i} className="text-danger text-[11px] p-1 rounded bg-danger/[0.04]">✕ {c.replace(/_/g, " ")}</div>
          ))}
        </div>
      )}

      {quality.recommended_next_actions?.length > 0 && (
        <div className="text-foreground/40 text-[11px] space-y-0.5">
          <div className="text-foreground/50">Actions</div>
          {quality.recommended_next_actions.slice(0, 3).map((a, i) => (
            <div key={i}>→ {a}</div>
          ))}
        </div>
      )}

      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
        Refresh
      </button>

      <div className="text-foreground/20 text-[11px]">{quality.scientific_boundary}</div>
    </div>
  );
}
