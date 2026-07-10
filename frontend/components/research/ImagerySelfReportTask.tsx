"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface ImagerySelfReportTaskProps {
  stimulusId: string;
  trialIndex: number;
  onComplete: (result: SelfReportTrialResult) => void;
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
  trialIndex,
  onComplete,
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

    const fixationTimer = setTimeout(() => {
      imageryOnsetMs.current = nowMs();
      imageryOnsetUtc.current = nowUtc();
      setPhase("imagine");
    }, 3000);

    return () => clearTimeout(fixationTimer);
  }, []);

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
  }, [trialIndex, stimulusId, vividness, confidence, effort, onComplete]);

  if (phase === "fixation") {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <div className="text-4xl mb-4">+</div>
        <p className="text-sm text-gray-400">Focus on the cross. Trial begins shortly...</p>
      </div>
    );
  }

  if (phase === "imagine") {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-lg font-medium">Close your eyes and imagine:</p>
        <p className="text-2xl text-emerald-400 font-semibold">
          {stimulusId.replace(/_/g, " ")}
        </p>
        <p className="text-sm text-gray-400 mt-8">
          When you have formed the image, click the button below.
        </p>
        <button
          onClick={handleImageFormed}
          className="mt-4 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 rounded-xl font-medium transition-colors"
        >
          Image Formed
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto space-y-6 p-6 bg-white/5 rounded-2xl border border-white/10">
      <h3 className="text-lg font-semibold">Rate Your Experience</h3>
      <p className="text-xs text-gray-500">
        These are subjective self-report ratings, not objective behavioral measures.
      </p>

      <div>
        <label className="block text-sm mb-2">
          Vividness: How vivid was your mental image? ({vividness}/7)
        </label>
        <input
          type="range"
          min={1} max={7} value={vividness}
          onChange={(e) => setVividness(Number(e.target.value))}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-gray-500">
          <span>No image</span><span>Perfectly vivid</span>
        </div>
      </div>

      <div>
        <label className="block text-sm mb-2">
          Confidence: How confident are you? ({confidence}/7)
        </label>
        <input
          type="range"
          min={1} max={7} value={confidence}
          onChange={(e) => setConfidence(Number(e.target.value))}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-gray-500">
          <span>Not at all</span><span>Very confident</span>
        </div>
      </div>

      <div>
        <label className="block text-sm mb-2">
          Effort: How much effort? ({effort}/7)
        </label>
        <input
          type="range"
          min={1} max={7} value={effort}
          onChange={(e) => setEffort(Number(e.target.value))}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-gray-500">
          <span>No effort</span><span>Maximum effort</span>
        </div>
      </div>

      <button
        onClick={handleSubmit}
        className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 rounded-xl font-medium transition-colors"
      >
        Submit Ratings
      </button>
    </div>
  );
}
