"use client";

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import ChartFrame from "@/components/charts/ChartFrame";

interface DataPoint {
  window: number;
  iqi: number;
  pid: number;
  attention: number;
  fatigue: number;
}

export default function TimelineChart({ data }: { data: DataPoint[] }) {
  return (
    <ChartFrame
      title="Proxy trajectory"
      description="Experimental proxy values across session windows. Higher IQI and attention are treated as stronger; lower PID and fatigue are treated as better. These are not clinical measurements."
      evidenceId="iqi.proxy"
      table={{
        columns: ["Window", "IQI", "PID", "Attention", "Fatigue"],
        rows: data.map((point) => [
          point.window,
          point.iqi.toFixed(2),
          point.pid.toFixed(2),
          point.attention.toFixed(2),
          point.fatigue.toFixed(2),
        ]),
      }}
    >
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <XAxis dataKey="window" tick={{ fontSize: 11, fill: "#888" }} />
          <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: "#888" }} />
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
    </ChartFrame>
  );
}
