"use client";

import { SafetyEvent } from "@/lib/types";
import { severityColor } from "@/lib/formatters";

export default function SafetyBanner({ events }: { events: SafetyEvent[] }) {
  if (events.length === 0) return null;
  const latest = events[events.length - 1];
  return (
    <div className={`mx-3 mt-2 p-3 rounded-lg border text-sm backdrop-blur ${severityColor(latest.severity)}`}>
      <div className="font-semibold text-xs uppercase tracking-[0.16em] mb-1">
        {latest.severity === "stop" ? "Session Stopped" : "Safety Monitor"}
      </div>
      <p className="text-foreground/80">
        {latest.event_type === "fatigue_high"
          ? "Fatigue proxy is rising. The scene has been simplified. Consider a short rest."
          : latest.message}
      </p>
      <p className="text-xs text-foreground/50 mt-1">
        This is not medical advice. If you feel distress, stop immediately.
      </p>
    </div>
  );
}
