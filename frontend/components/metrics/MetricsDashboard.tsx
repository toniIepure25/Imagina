"use client";

import MetricCard from "./MetricCard";
import TimelineChart from "./TimelineChart";
import { interpretationColor } from "@/lib/formatters";

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
        <MetricCard label="PID" value={pid} subtitle="Proxy, lower is better" color="text-yellow-400" />
        <MetricCard label="Attention" value={attention} subtitle="Higher is better" color="text-green-400" />
        <MetricCard label="Fatigue" value={fatigue} subtitle="Lower is better" color="text-red-400" />
        <div className="col-span-2">
          <MetricCard label="Uncertainty" value={uncertainty} subtitle="Experimental confidence proxy, lower is better" color="text-sky-300" />
        </div>
      </div>
      <div className="glass p-3 panel-glow">
        <div className="flex justify-between items-center mb-2">
          <span className="text-[10px] uppercase tracking-[0.16em] text-foreground/45">Live Timeline</span>
          <span className={`text-xs font-medium ${interpretationColor(interpretation)}`}>
            {interpretation}
          </span>
        </div>
        <TimelineChart data={timeline} />
      </div>
    </div>
  );
}
