"use client";

import Button from "../common/Button";
import Badge from "../common/Badge";
import { formatDuration } from "@/lib/formatters";

interface Props {
  status: string;
  elapsed: number;
  level: number;
  levelName: string;
  mode?: string;
  taskName?: string;
  connectionStatus?: string;
  onStop: () => void;
}

export default function SessionControls({
  status,
  elapsed,
  level,
  levelName,
  mode = "Simulated",
  taskName = "Dream Corridor Stabilization",
  connectionStatus = "disconnected",
  onStop,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3 px-4 py-3 border-b border-surface-border bg-background/72 backdrop-blur-md">
      <div>
        <div className="text-[10px] uppercase tracking-[0.18em] text-foreground/40">Current Task</div>
        <div className="text-sm font-semibold text-foreground/85">{taskName}</div>
      </div>
      <Badge color={status === "running" ? "bg-green-500/20 text-green-300" : "bg-foreground/10 text-foreground/50"}>
        {status}
      </Badge>
      <Badge color="bg-accent/15 text-accent-glow">{mode}</Badge>
      <span className="text-sm font-mono text-foreground/70 tabular-nums">{formatDuration(elapsed)}</span>
      <Badge color="bg-cyan-500/10 text-cyan-200">Lvl {level}: {levelName}</Badge>
      <span className="text-xs text-foreground/45">WS: {connectionStatus}</span>
      <div className="flex-1" />
      {status === "running" && (
        <Button variant="danger" size="sm" onClick={onStop}>End Session</Button>
      )}
    </div>
  );
}
