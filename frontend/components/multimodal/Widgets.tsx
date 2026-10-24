"use client";

import { useState, type ReactNode } from "react";
import { EVIDENCE_LABELS, SOURCE_LABELS, type EvidenceClass, type SourceKind } from "@/lib/multimodalApi";

export function Panel({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-surface-border bg-surface/30 p-4 space-y-3">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-[11px] uppercase tracking-[0.2em] text-accent-glow/70">{title}</h2>
        {hint && <span className="text-[10px] text-foreground/40">{hint}</span>}
      </div>
      {children}
    </section>
  );
}

const SOURCE_STYLE: Record<SourceKind, string> = {
  SYNTHETIC: "border-foreground/30 text-foreground/70 bg-foreground/5",
  REPLAY: "border-accent/50 text-accent-glow bg-accent/10",
  REAL_SENSOR: "border-warning/60 text-warning bg-warning/10",
};

export function SourceBadge({ kind }: { kind: SourceKind }) {
  return (
    <span className={`rounded border px-2 py-0.5 text-[10px] font-mono tracking-wider ${SOURCE_STYLE[kind]}`}>
      {SOURCE_LABELS[kind]}
    </span>
  );
}

const EVIDENCE_GLYPH: Record<EvidenceClass, string> = {
  DIRECT_MEASUREMENT: "●",
  DERIVED_METRIC: "◆",
  VALIDATED_ESTIMATE: "✓",
  EXPERIMENTAL_PROXY: "△",
  SUBJECTIVE_REPORT: "✎",
};

export function EvidenceBadge({ evidence }: { evidence: EvidenceClass }) {
  const proxy = evidence === "EXPERIMENTAL_PROXY";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] ${
        proxy ? "border-warning/40 text-warning/90" : "border-surface-border text-foreground/60"
      }`}
    >
      <span aria-hidden>{EVIDENCE_GLYPH[evidence]}</span>
      {EVIDENCE_LABELS[evidence]}
    </span>
  );
}

export function DimensionBar({ name, value, uncertainty, evidence }: {
  name: string; value: number | null; uncertainty: number | null; evidence: EvidenceClass;
}) {
  const pct = value === null ? 0 : Math.round(value * 100);
  const lo = value === null || uncertainty === null ? null : Math.max(0, value - uncertainty);
  const hi = value === null || uncertainty === null ? null : Math.min(1, value + uncertainty);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="text-foreground/80">{name.replaceAll("_", " ")}</span>
        <EvidenceBadge evidence={evidence} />
      </div>
      <div className="relative h-2 rounded bg-foreground/10" role="img"
           aria-label={`${name} ${value === null ? "not available" : value.toFixed(2)}`}>
        {lo !== null && hi !== null && (
          <div className="absolute inset-y-0 rounded bg-accent/25" style={{ left: `${lo * 100}%`, width: `${(hi - lo) * 100}%` }} />
        )}
        {value !== null && (
          <div className="absolute inset-y-0 w-1 -ml-0.5 rounded bg-accent-glow" style={{ left: `${pct}%` }} />
        )}
      </div>
      <div className="text-[10px] text-foreground/45 font-mono">
        {value === null ? "not estimated" : `${value.toFixed(2)}${uncertainty !== null ? ` ± ${uncertainty.toFixed(2)}` : ""}`}
      </div>
    </div>
  );
}

export function Sparkline({ title, unit, points, height = 44 }: {
  title: string; unit: string; points: { t: number; v: number | null }[]; height?: number;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const valid = points.filter((p): p is { t: number; v: number } => p.v !== null && Number.isFinite(p.v));
  const width = 220;
  if (valid.length < 2) {
    return (
      <div className="text-[11px] text-foreground/40">
        <div className="text-foreground/70">{title}</div>insufficient data
      </div>
    );
  }
  const t0 = valid[0].t;
  const t1 = valid[valid.length - 1].t;
  let vmin = Math.min(...valid.map((p) => p.v));
  let vmax = Math.max(...valid.map((p) => p.v));
  if (vmax - vmin < 1e-9) { vmin -= 1; vmax += 1; }
  const x = (t: number) => ((t - t0) / Math.max(t1 - t0, 1e-9)) * (width - 8) + 4;
  const y = (v: number) => height - 4 - ((v - vmin) / (vmax - vmin)) * (height - 8);
  const path = valid.map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ");
  const shown = hover !== null ? valid[hover] : valid[valid.length - 1];
  const fmt = (v: number) => (Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 1 ? v.toFixed(2) : v.toFixed(3));
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between text-[11px]">
        <span className="text-foreground/70">{title}</span>
        <span className="font-mono text-foreground/90">{fmt(shown.v)} <span className="text-foreground/40">{unit}</span>
          {hover !== null && <span className="text-foreground/40"> @ {shown.t.toFixed(0)}s</span>}</span>
      </div>
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="overflow-visible"
           onMouseLeave={() => setHover(null)}
           onMouseMove={(e) => {
             const r = e.currentTarget.getBoundingClientRect();
             const tx = t0 + ((e.clientX - r.left) / r.width) * (t1 - t0);
             let best = 0;
             valid.forEach((p, i) => { if (Math.abs(p.t - tx) < Math.abs(valid[best].t - tx)) best = i; });
             setHover(best);
           }}>
        <line x1={4} x2={width - 4} y1={height - 4} y2={height - 4} stroke="currentColor" className="text-foreground/10" />
        <path d={path} fill="none" stroke="var(--accent-glow)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        {hover !== null && (
          <>
            <line x1={x(shown.t)} x2={x(shown.t)} y1={2} y2={height - 2} stroke="currentColor" className="text-foreground/30" />
            <circle cx={x(shown.t)} cy={y(shown.v)} r={4} fill="var(--accent-glow)" stroke="var(--background)" strokeWidth={2} />
          </>
        )}
      </svg>
    </div>
  );
}
