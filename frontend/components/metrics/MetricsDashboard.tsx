"use client";

import dynamic from "next/dynamic";
import MetricCard from "./MetricCard";
import { interpretationColor } from "@/lib/formatters";

const TimelineChart = dynamic(() => import("./TimelineChart"), {
  ssr: false,
  loading: () => (
    <div
      role="status"
      aria-label="Loading proxy timeline"
      className="flex h-[200px] items-center justify-center font-mono text-[11px] uppercase tracking-[0.16em] text-foreground/30"
    >
      Loading timeline…
    </div>
  ),
});

interface Props {
  iqi: number;
  pid: number;
  attention: number;
  fatigue: number;
  uncertainty: number;
  interpretation: string;
  timeline: { window: number; iqi: number; pid: number; attention: number; fatigue: number }[];
}

export default function MetricsDashboard({ iqi, pid, attention, fatigue, uncertainty, interpretation, timeline }: Props) {
  return (
    <div className="space-y-3 p-3">
      <div className="grid grid-cols-2 gap-2">
        <MetricCard label="IQI" value={iqi} subtitle="Proxy, higher is better" />
        <MetricCard label="PID" value={pid} subtitle="Proxy, lower is better" color="text-lock" />
        <MetricCard label="Attention" value={attention} subtitle="Higher is better" color="text-signal" />
        <MetricCard label="Fatigue" value={fatigue} subtitle="Lower is better" color="text-danger" />
        <div className="col-span-2">
          <MetricCard label="Uncertainty" value={uncertainty} subtitle="Experimental confidence proxy, lower is better" color="text-accent-glow" />
        </div>
      </div>
      <div className="glass p-3 panel-glow">
        <div className="flex justify-between items-center mb-2">
          <span className="text-[11px] uppercase tracking-[0.16em] text-foreground/45">Live Timeline</span>
          <span className={`text-xs font-medium ${interpretationColor(interpretation)}`}>
            {interpretation}
          </span>
        </div>
        <TimelineChart data={timeline} />
      </div>
    </div>
  );
}
