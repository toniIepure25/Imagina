"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface BehavioralTaskProps {
  stimulusId: string;
  trialIndex: number;
  onComplete: (result: TrialResult) => void;
}

export interface TrialResult {
  trial_index: number;
  stimulus_id: string;
  vividness: number;
  confidence: number;
  effort: number;
  response_time_ms: number;
}

export default function BehavioralTask({ stimulusId, trialIndex, onComplete }: BehavioralTaskProps) {
  const [phase, setPhase] = useState<"fixation" | "imagine" | "rate">("fixation");
  const [vividness, setVividness] = useState(4);
  const [confidence, setConfidence] = useState(4);
  const [effort, setEffort] = useState(4);
  const startTimeRef = useRef(0);

  useEffect(() => {
    startTimeRef.current = Date.now();
    const fixationTimer = setTimeout(() => {
      setPhase("imagine");
      startTimeRef.current = Date.now();
    }, 3000);
    return () => clearTimeout(fixationTimer);
  }, []);

  const handleImagineComplete = useCallback(() => {
    setPhase("rate");
  }, []);

  const handleSubmit = useCallback(() => {
    const responseTime = Date.now() - startTimeRef.current;
    onComplete({
      trial_index: trialIndex,
      stimulus_id: stimulusId,
      vividness,
      confidence,
      effort,
      response_time_ms: responseTime,
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
        <p className="text-2xl text-emerald-400 font-semibold">{stimulusId.replace(/_/g, " ")}</p>
        <p className="text-sm text-gray-400 mt-8">
          When you have formed the image, click the button below.
        </p>
        <button
          onClick={handleImagineComplete}
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
