"use client";

import { useMemo } from "react";
import { CONDITIONING_KEYS, type ImagineConditioning } from "@/lib/imagine/types";

const SHORT: Record<string, string> = {
  attention: "ATT",
  arousal: "ARO",
  valence: "VAL",
  vividness: "VIV",
  fatigue: "FAT",
  confidence: "CON",
  theta: "θ",
  alpha: "α",
  beta: "β",
  gamma: "γ",
  hrv: "HRV",
  eda: "EDA",
  signal_quality: "Q",
  uncertainty: "U",
  trend: "TR",
  stability: "ST",
};

export default function SignalConstellation({ conditioning }: { conditioning: ImagineConditioning }) {
  const points = useMemo(() => {
    const center = 120;
    const radius = 82;
    return CONDITIONING_KEYS.map((key, index) => {
      const angle = (index / CONDITIONING_KEYS.length) * Math.PI * 2 - Math.PI / 2;
      const value = Math.max(0.04, conditioning.vector[key]);
      return {
        key,
        label: SHORT[key] ?? key,
        x: center + Math.cos(angle) * radius * value,
        y: center + Math.sin(angle) * radius * value,
        labelX: center + Math.cos(angle) * (radius + 14),
        labelY: center + Math.sin(angle) * (radius + 14),
        angle,
        value,
      };
    });
  }, [conditioning]);

  const polygon = points.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
      <div className="flex items-center justify-between">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-foreground/35">16D conditioning</p>
        <span className="font-mono text-[11px] text-signal/70">{conditioning.vectorHash.slice(0, 8)}</span>
      </div>
      <svg viewBox="0 0 240 240" role="img" aria-label="Radar of sixteen derived conditioning dimensions" className="mx-auto mt-1 h-auto w-full max-w-[250px]">
        {[0.33, 0.66, 1].map((scale) => (
          <circle
            key={scale}
            cx="120"
            cy="120"
            r={82 * scale}
            fill="none"
            stroke="rgba(255,255,255,0.09)"
            strokeWidth="0.8"
          />
        ))}
        {points.map((point) => (
          <line
            key={`spoke-${point.key}`}
            x1="120"
            y1="120"
            x2={120 + Math.cos(point.angle) * 82}
            y2={120 + Math.sin(point.angle) * 82}
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="0.8"
          />
        ))}
        <polygon points={polygon} fill="rgba(111,227,196,0.15)" stroke="#6fe3c4" strokeWidth="1.4" />
        {points.map((point) => (
          <g key={point.key}>
            <circle cx={point.x} cy={point.y} r="2" fill="#d9fff5" />
            <text
              x={point.labelX}
              y={point.labelY}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="rgba(232,238,255,0.45)"
              fontSize="11"
              fontFamily="monospace"
            >
              {point.label}
            </text>
          </g>
        ))}
      </svg>
      <table className="sr-only">
        <caption>Derived conditioning values</caption>
        <tbody>
          {CONDITIONING_KEYS.map((key) => (
            <tr key={key}>
              <th scope="row">{key}</th>
              <td>{Math.round(conditioning.vector[key] * 100)} percent</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
