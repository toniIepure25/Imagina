"use client";

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";

interface DataPoint {
  window: number;
  iqi: number;
  pid: number;
  attention: number;
  fatigue: number;
}

export default function TimelineChart({ data }: { data: DataPoint[] }) {
  if (data.length === 0) {
    return <div className="text-xs text-foreground/30 text-center py-8">Waiting for data...</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <XAxis dataKey="window" tick={{ fontSize: 10, fill: "#666" }} />
        <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: "#666" }} />
        <Tooltip
          contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 8, fontSize: 12 }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Line type="monotone" dataKey="iqi" stroke="#818cf8" strokeWidth={2} dot={false} name="IQI" />
        <Line type="monotone" dataKey="pid" stroke="#f59e0b" strokeWidth={2} dot={false} name="PID" />
        <Line type="monotone" dataKey="attention" stroke="#22c55e" strokeWidth={1} dot={false} name="Attention" />
        <Line type="monotone" dataKey="fatigue" stroke="#ef4444" strokeWidth={1} dot={false} name="Fatigue" />
      </LineChart>
    </ResponsiveContainer>
  );
}
