"use client";

import type { AdaptiveTarget } from "@/lib/imagineScene";

export interface AdaptiveSample {
  at: number;
  attention: number;
  valence: number;
  intervention: boolean;
  safetyStop: "fatigue" | "quality" | null;
}

export default function AdaptiveTrace({
  samples,
  target,
  reason,
}: {
  samples: AdaptiveSample[];
  target: AdaptiveTarget;
  reason: string;
}) {
  const width = 320;
  const height = 78;
  const visible = samples.slice(-60);
  const point = (value: number, index: number) => {
    const x = visible.length > 1 ? (index / (visible.length - 1)) * width : 0;
    const y = height - 8 - Math.max(0, Math.min(1, value)) * (height - 16);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  };
  const attention = visible.map((sample, index) => point(sample.attention, index)).join(" ");
  const valence = visible.map((sample, index) => point(sample.valence, index)).join(" ");
  const bandTop = height - 8 - target.target.attention * (height - 16);
  const markers = visible
    .map((sample, index) => ({ sample, index }))
    .filter(({ sample }) => sample.intervention || sample.safetyStop);

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3" data-testid="adaptive-trace">
      <div className="flex items-center justify-between gap-2">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-foreground/35">Adaptive trace</p>
        <span className="font-mono text-[11px] text-foreground/35">{target.label}</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="mt-2 h-[78px] w-full" role="img" aria-label="adaptive trace">
        <rect x="0" y="0" width={width} height={height} fill="rgba(5,7,17,0.25)" rx="4" />
        <rect
          x="0"
          y={bandTop - 5}
          width={width}
          height="10"
          fill="rgba(111,227,196,0.08)"
          stroke="rgba(111,227,196,0.18)"
          strokeWidth="0.6"
        />
        <polyline points={valence} fill="none" stroke="rgba(157,135,255,0.65)" strokeWidth="1.2" />
        <polyline points={attention} fill="none" stroke="#6fe3c4" strokeWidth="1.6" />
        {markers.map(({ sample, index }) => (
          <line
            key={`${sample.at}-${index}`}
            x1={visible.length > 1 ? (index / (visible.length - 1)) * width : 0}
            x2={visible.length > 1 ? (index / (visible.length - 1)) * width : 0}
            y1="0"
            y2={height}
            stroke={sample.safetyStop ? "#f0a36b" : "rgba(255,255,255,0.22)"}
            strokeDasharray="2 3"
            strokeWidth="1"
          />
        ))}
      </svg>
      <div className="mt-1 flex items-center justify-between font-mono text-[11px] text-foreground/35">
        <span>attention</span>
        <span className="text-[#9d87ff]">valence</span>
        <span>60 s demo</span>
      </div>
      <p className="mt-2 line-clamp-2 text-[11px] leading-5 text-foreground/40">{reason}</p>
      <table className="sr-only">
        <caption>Adaptive samples</caption>
        <tbody>
          {visible.slice(-8).map((sample) => (
            <tr key={sample.at}>
              <th scope="row">{new Date(sample.at).toISOString()}</th>
              <td>{Math.round(sample.attention * 100)} attention</td>
              <td>{sample.intervention ? "intervention" : "hold"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
