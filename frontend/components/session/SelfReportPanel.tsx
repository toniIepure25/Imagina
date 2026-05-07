"use client";

import { useState } from "react";
import Button from "../common/Button";
import Slider from "../common/Slider";

interface Props {
  onSubmit: (report: {
    vividness: number;
    stability: number;
    focus: number;
    relaxation: number;
    effort: number;
    fatigue: number;
    distraction: number;
    notes: string;
  }) => void;
}

export default function SelfReportPanel({ onSubmit }: Props) {
  const [vividness, setVividness] = useState(5);
  const [stability, setStability] = useState(5);
  const [focus, setFocus] = useState(5);
  const [relaxation, setRelaxation] = useState(5);
  const [effort, setEffort] = useState(5);
  const [fatigue, setFatigue] = useState(3);
  const [distraction, setDistraction] = useState(3);
  const [notes, setNotes] = useState("");

  const submit = () => {
    onSubmit({ vividness, stability, focus, relaxation, effort, fatigue, distraction, notes });
  };

  return (
    <div className="space-y-3 p-3">
      <div>
        <h3 className="text-sm font-semibold text-foreground/80">Self Report</h3>
        <p className="text-[11px] text-foreground/42">Quick subjective inputs for future proxy estimates.</p>
      </div>
      <div className="space-y-1.5">
        <Slider label="Vividness" value={vividness} onChange={setVividness} />
        <Slider label="Stability" value={stability} onChange={setStability} />
        <Slider label="Focus" value={focus} onChange={setFocus} />
        <Slider label="Relaxation" value={relaxation} onChange={setRelaxation} />
        <Slider label="Effort" value={effort} onChange={setEffort} />
        <Slider label="Fatigue" value={fatigue} onChange={setFatigue} />
        <Slider label="Distraction" value={distraction} onChange={setDistraction} />
      </div>
      <textarea
        className="w-full px-2 py-1 rounded bg-surface border border-surface-border text-xs text-foreground/80 resize-none h-12 outline-none focus:border-accent"
        placeholder="Notes (optional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      <Button variant="secondary" size="sm" onClick={submit} className="w-full">
        Submit Report
      </Button>
    </div>
  );
}
