"use client";

import { SessionSummary } from "@/lib/types";
import { pct, fixed, formatDuration } from "@/lib/formatters";
import Button from "../common/Button";
import Card from "../common/Card";
import Link from "next/link";

export default function SessionSummaryCard({ summary }: { summary: SessionSummary }) {
  return (
    <Card className="max-w-lg mx-auto space-y-4">
      <h2 className="text-xl font-bold">Session Complete</h2>
      {summary.calibration_quality_score != null && (
        <div className="rounded-lg border border-accent/20 bg-accent/8 p-3 text-sm">
          Calibration quality <span className="font-mono text-accent-glow">{pct(summary.calibration_quality_score)}</span>
          {summary.signal_provider_id && <span className="ml-2 text-foreground/45">via {summary.signal_provider_id}</span>}
          {summary.scenario && <span className="ml-2 text-foreground/45">({summary.scenario})</span>}
        </div>
      )}
      {summary.experiment_run_id && (
        <div className="rounded-lg border border-surface-border bg-surface/30 p-3 text-xs text-foreground/55">
          Linked to experiment run <span className="font-mono">{summary.experiment_run_id.slice(0,8)}</span>
        </div>
      )}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-foreground/50">Duration</div>
          <div className="font-mono">{formatDuration(summary.duration_seconds)}</div>
        </div>
        <div>
          <div className="text-foreground/50">Avg IQI</div>
          <div className="font-mono">{pct(summary.average_iqi)}</div>
        </div>
        <div>
          <div className="text-foreground/50">Best IQI</div>
          <div className="font-mono">{pct(summary.best_iqi)}</div>
        </div>
        <div>
          <div className="text-foreground/50">Avg PID</div>
          <div className="font-mono">{fixed(summary.average_pid)}</div>
        </div>
        <div>
          <div className="text-foreground/50">Best PID</div>
          <div className="font-mono">{fixed(summary.best_pid)}</div>
        </div>
        <div>
          <div className="text-foreground/50">Max Level</div>
          <div className="font-mono">{summary.max_level_reached}</div>
        </div>
        <div>
          <div className="text-foreground/50">Best Streak</div>
          <div className="font-mono">{formatDuration(summary.best_stability_streak_seconds)}</div>
        </div>
        <div>
          <div className="text-foreground/50">Fatigue Peak</div>
          <div className="font-mono">{pct(summary.fatigue_peak)}</div>
        </div>
        <div>
          <div className="text-foreground/50">Safety Events</div>
          <div className="font-mono">{summary.safety_events_count}</div>
        </div>
      </div>
      {summary.recommendation && (
        <p className="text-sm text-foreground/60 italic">{summary.recommendation}</p>
      )}
      <div className="flex gap-3">
        <Link href={`/reports/${summary.session_id}`}>
          <Button variant="secondary" size="sm">View Full Report</Button>
        </Link>
        <Link href="/">
          <Button variant="ghost" size="sm">Back to Home</Button>
        </Link>
      </div>
    </Card>
  );
}
