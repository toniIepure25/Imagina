export function pct(v: number): string {
  return `${(v * 100).toFixed(0)}%`;
}

export function fixed(v: number, digits = 2): string {
  return v.toFixed(digits);
}

export function interpretationColor(interp: string): string {
  switch (interp) {
    case "excellent":
      return "text-green-400";
    case "good":
      return "text-blue-400";
    case "unstable":
      return "text-yellow-400";
    case "fatigue_risk":
      return "text-red-400";
    default:
      return "text-foreground/50";
  }
}

export function severityColor(severity: string): string {
  switch (severity) {
    case "stop":
      return "bg-red-900/60 border-red-500";
    case "warning":
      return "bg-yellow-900/40 border-yellow-500";
    default:
      return "bg-blue-900/30 border-blue-500";
  }
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
