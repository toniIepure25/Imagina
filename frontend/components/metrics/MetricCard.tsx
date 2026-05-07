"use client";

import { pct } from "@/lib/formatters";

interface Props {
  label: string;
  value: number;
  subtitle?: string;
  color?: string;
}

export default function MetricCard({ label, value, subtitle, color = "text-accent-glow" }: Props) {
  return (
    <div className="glass metric-transition p-3 text-center panel-glow">
      <div className="text-[10px] uppercase tracking-[0.16em] text-foreground/45 mb-1">{label}</div>
      <div className={`text-2xl font-bold font-mono tabular-nums transition-colors duration-300 ${color}`}>{pct(value)}</div>
      {subtitle && <div className="text-[11px] text-foreground/42 mt-1 leading-tight">{subtitle}</div>}
    </div>
  );
}
