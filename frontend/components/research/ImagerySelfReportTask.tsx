"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface ImagerySelfReportTaskProps {
  stimulusId: string;
  stimulusLabel?: string;
  trialIndex: number;
  onComplete: (result: SelfReportTrialResult) => void;
  onAbort?: () => void;
  fixationMs?: number;
}

export interface SelfReportTrialResult {
  trial_index: number;
  stimulus_id: string;
  vividness: number;
  confidence: number;
  effort: number;
  fixation_onset_ms: number;
  imagery_onset_ms: number;
  image_formed_ms: number;
  rating_screen_onset_ms: number;
  rating_submission_ms: number;
  imagery_formation_latency_ms: number;
  rating_completion_latency_ms: number;
  fixation_onset_utc: string;
  imagery_onset_utc: string;
  image_formed_utc: string;
  rating_screen_onset_utc: string;
  rating_submission_utc: string;
}

function nowMs(): number {
  return performance.now();
}

function nowUtc(): string {
  return new Date().toISOString();
}

export default function ImagerySelfReportTask({
  stimulusId,
  stimulusLabel,
  trialIndex,
  onComplete,
  onAbort,
  fixationMs = 3000,
}: ImagerySelfReportTaskProps) {
  const [phase, setPhase] = useState<"fixation" | "imagine" | "rate">("fixation");
  const [vividness, setVividness] = useState(4);
  const [confidence, setConfidence] = useState(4);
  const [effort, setEffort] = useState(4);

  const fixationOnsetMs = useRef(0);
  const fixationOnsetUtc = useRef("");
  const imageryOnsetMs = useRef(0);
  const imageryOnsetUtc = useRef("");
  const imageFormedMs = useRef(0);
  const imageFormedUtc = useRef("");
  const ratingScreenOnsetMs = useRef(0);
  const ratingScreenOnsetUtc = useRef("");

  useEffect(() => {
    fixationOnsetMs.current = nowMs();
    fixationOnsetUtc.current = nowUtc();

    const fixationTimer = window.setTimeout(() => {
      imageryOnsetMs.current = nowMs();
      imageryOnsetUtc.current = nowUtc();
      setPhase("imagine");
    }, fixationMs);

    return () => window.clearTimeout(fixationTimer);
  }, [fixationMs]);

  const handleImageFormed = useCallback(() => {
    imageFormedMs.current = nowMs();
    imageFormedUtc.current = nowUtc();
    ratingScreenOnsetMs.current = nowMs();
    ratingScreenOnsetUtc.current = nowUtc();
    setPhase("rate");
  }, []);

  const handleSubmit = useCallback(() => {
    const submissionMs = nowMs();
    const submissionUtc = nowUtc();

    onComplete({
      trial_index: trialIndex,
      stimulus_id: stimulusId,
      vividness,
      confidence,
      effort,
      fixation_onset_ms: fixationOnsetMs.current,
      imagery_onset_ms: imageryOnsetMs.current,
      image_formed_ms: imageFormedMs.current,
      rating_screen_onset_ms: ratingScreenOnsetMs.current,
      rating_submission_ms: submissionMs,
      imagery_formation_latency_ms: imageFormedMs.current - imageryOnsetMs.current,
      rating_completion_latency_ms: submissionMs - ratingScreenOnsetMs.current,
      fixation_onset_utc: fixationOnsetUtc.current,
      imagery_onset_utc: imageryOnsetUtc.current,
      image_formed_utc: imageFormedUtc.current,
      rating_screen_onset_utc: ratingScreenOnsetUtc.current,
      rating_submission_utc: submissionUtc,
    });
  }, [confidence, effort, onComplete, stimulusId, trialIndex, vividness]);

  return (
    <div aria-live="polite">
      {phase === "fixation" ? (
        <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-surface-border bg-white/[0.025] p-6 text-center">
          <div className="grid h-14 w-14 place-items-center rounded-full border border-surface-border font-mono text-2xl text-signal">
            +
          </div>
          <p className="mt-4 text-sm text-foreground/55">Focus on the cross. The imagery prompt begins shortly.</p>
          <p className="mt-1 font-mono text-[11px] text-foreground/30">
            Trial {trialIndex + 1} · fixation {Math.round(fixationMs / 1000)} s
          </p>
        </div>
      ) : null}

      {phase === "imagine" ? (
        <div className="flex min-h-64 flex-col items-center justify-center gap-4 rounded-xl border border-surface-border bg-white/[0.025] p-6 text-center">
          <p className="text-sm text-foreground/55">Close your eyes, or look away, and imagine:</p>
          <p className="text-2xl font-semibold text-signal">{stimulusLabel ?? stimulusId.replaceAll("_", " ")}</p>
          <p className="max-w-sm text-[11px] leading-5 text-foreground/35">
            There is no correct image and no image is recorded. This is a self-report demonstration.
          </p>
          <button
            type="button"
            onClick={handleImageFormed}
            className="mt-2 inline-flex min-h-11 items-center rounded-lg border border-signal/35 bg-signal/[0.09] px-5 text-sm font-medium text-signal hover:bg-signal/[0.14]"
          >
            Image formed
          </button>
          {onAbort ? (
            <button
              type="button"
              onClick={onAbort}
              className="min-h-11 rounded-lg px-3 text-[11px] text-foreground/40 hover:text-foreground/70"
            >
              Stop demonstration
            </button>
          ) : null}
        </div>
      ) : null}

      {phase === "rate" ? (
        <div className="mx-auto max-w-md space-y-6 rounded-xl border border-surface-border bg-white/[0.025] p-6">
          <div>
            <h2 className="text-lg font-semibold">Rate the experience</h2>
            <p className="mt-1 text-[11px] leading-5 text-foreground/40">
              Subjective self-report only. Not an objective measure of imagery.
            </p>
          </div>

          {[
            {
              id: "vividness",
              label: "Vividness",
              value: vividness,
              set: setVividness,
              low: "No image",
              high: "Perfectly vivid",
            },
            {
              id: "confidence",
              label: "Confidence",
              value: confidence,
              set: setConfidence,
              low: "Not at all",
              high: "Very confident",
            },
            {
              id: "effort",
              label: "Effort",
              value: effort,
              set: setEffort,
              low: "No effort",
              high: "Maximum effort",
            },
          ].map((item) => (
            <div key={item.id}>
              <label htmlFor={`rating-${item.id}`} className="block text-sm text-foreground/70">
                {item.label}: {item.value}/7
              </label>
              <input
                id={`rating-${item.id}`}
                type="range"
                min={1}
                max={7}
                value={item.value}
                onChange={(event) => item.set(Number(event.target.value))}
                className="mt-2 h-11 w-full accent-[var(--signal)]"
              />
              <div className="flex justify-between text-[11px] text-foreground/35">
                <span>{item.low}</span>
                <span>{item.high}</span>
              </div>
            </div>
          ))}

          <button
            type="button"
            onClick={handleSubmit}
            className="inline-flex min-h-11 w-full items-center justify-center rounded-lg border border-signal/35 bg-signal/[0.09] px-4 text-sm font-medium text-signal hover:bg-signal/[0.14]"
          >
            Submit ratings
          </button>
          {onAbort ? (
            <button
              type="button"
              onClick={onAbort}
              className="min-h-11 w-full rounded-lg px-3 text-[11px] text-foreground/40 hover:text-foreground/70"
            >
              Stop demonstration
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
