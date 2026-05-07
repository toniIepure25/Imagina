"use client";

import { useEffect, useState } from "react";
import Button from "../common/Button";
import Slider from "../common/Slider";
import { apiFetch } from "@/lib/api";
import { pct } from "@/lib/formatters";
import type { CalibrationProfile } from "@/lib/types";

interface Props {
  sessionId: string;
  providerId: string;
  onComplete: (
    baseline: { focus: number; relaxation: number; vividness: number; fatigue: number },
    calibration: CalibrationProfile,
  ) => void;
}

export default function BaselineCalibration({ sessionId, providerId, onComplete }: Props) {
  const [focus, setFocus] = useState(5);
  const [relaxation, setRelaxation] = useState(5);
  const [vividness, setVividness] = useState(5);
  const [fatigue, setFatigue] = useState(3);
  const [timer, setTimer] = useState(30);
  const [started, setStarted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [calibration, setCalibration] = useState<CalibrationProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!started) return;
    if (timer <= 0) return;
    const id = setInterval(() => setTimer((t) => t - 1), 1000);
    return () => clearInterval(id);
  }, [started, timer]);

  const start = async () => {
    setError(null);
    setCalibration(null);
    setTimer(30);
    await apiFetch(`/api/sessions/${sessionId}/calibration/start`, { method: "POST" });
    setStarted(true);
  };

  const complete = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const result = await apiFetch<CalibrationProfile>(`/api/sessions/${sessionId}/calibration/complete`, {
        method: "POST",
        body: JSON.stringify({
          duration_seconds: 30,
          mode: providerId.includes("manual") ? "manual" : providerId.includes("replay") ? "replay" : "simulated",
          focus,
          relaxation,
          vividness,
          fatigue,
          notes: "",
        }),
      });
      setCalibration(result);
    } catch {
      setError("Calibration could not be completed. Check the backend and try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-md mx-auto space-y-6 p-6">
      <h2 className="text-xl font-bold">Baseline Calibration</h2>
      <p className="text-sm text-foreground/60">
        Sit comfortably and stabilize attention. IMAGINA calibrates session-local proxy baselines, not mental content.
      </p>
      <div className="rounded-lg border border-surface-border bg-surface/35 p-3 text-xs text-foreground/55">
        Provider: <span className="font-mono text-accent-glow">{providerId}</span>
      </div>

      {!started ? (
        <Button onClick={start} className="w-full">
          Start Calibration (30s)
        </Button>
      ) : (
        <>
          <div className="text-center text-3xl font-mono text-accent-glow">
            {timer > 0 ? `0:${timer.toString().padStart(2, "0")}` : "Ready"}
          </div>
          <div className="space-y-3">
            <Slider label="Focus" value={focus} onChange={setFocus} />
            <Slider label="Relaxation" value={relaxation} onChange={setRelaxation} />
            <Slider label="Vividness" value={vividness} onChange={setVividness} />
            <Slider label="Fatigue" value={fatigue} onChange={setFatigue} />
          </div>
          <Button
            disabled={timer > 0 || submitting}
            onClick={complete}
            className="w-full"
          >
            {timer > 0 ? "Wait for calibration..." : submitting ? "Computing..." : "Compute Calibration Quality"}
          </Button>
          {calibration && (
            <div className="rounded-lg border border-accent/25 bg-accent/8 p-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">Calibration quality</span>
                <span className="font-mono text-accent-glow">{pct(calibration.calibration_quality_score)}</span>
              </div>
              {calibration.warnings.length > 0 && (
                <div className="mt-2 text-xs text-yellow-200">
                  Warnings: {calibration.warnings.join(", ")}. You can continue, but results may be noisier.
                </div>
              )}
              <div className="mt-3 flex gap-2">
                <Button
                  size="sm"
                  onClick={() => onComplete({ focus, relaxation, vividness, fatigue }, calibration)}
                >
                  Continue
                </Button>
                <Button size="sm" variant="secondary" onClick={() => { setStarted(false); setCalibration(null); }}>
                  Recalibrate
                </Button>
              </div>
            </div>
          )}
          {error && <div className="text-sm text-danger">{error}</div>}
        </>
      )}
    </div>
  );
}
