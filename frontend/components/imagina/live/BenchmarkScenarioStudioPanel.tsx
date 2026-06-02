"use client";

import { useState } from "react";

interface ValidationResult {
  valid: boolean; quality_score: number; category_scores: Record<string, number>;
  warnings: string[]; errors: string[]; forbidden_terms_found: string[];
  runnable: boolean; safe_to_import: boolean; scientific_boundary?: string;
}

interface SdkStudioProps {
  userId?: string;
  onRunScenario: (sid: string) => void;
  onImport: (payload: Record<string, unknown>) => void;
  onValidate: (payload: Record<string, unknown>) => Promise<ValidationResult | null>;
  onGetExample: () => Promise<Record<string, unknown> | null>;
}

export function BenchmarkScenarioStudioPanel({
  userId, onRunScenario, onImport, onValidate, onGetExample,
}: SdkStudioProps) {
  const [editorText, setEditorText] = useState("{}");
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [scenarioId, setScenarioId] = useState("");

  const handleValidate = async () => {
    try {
      const payload = JSON.parse(editorText);
      const v = await onValidate(payload);
      setValidation(v);
    } catch { setValidation({ valid: false, quality_score: 0, category_scores: {}, warnings: [], errors: ["Invalid JSON"], forbidden_terms_found: [], runnable: false, safe_to_import: false } as ValidationResult); }
  };

  const handleLoadExample = async () => {
    const ex = await onGetExample();
    if (ex) setEditorText(JSON.stringify(ex, null, 2));
  };

  const handleImport = () => {
    try {
      const payload = JSON.parse(editorText);
      onImport(payload);
    } catch { /* invalid JSON handled by validate */ }
  };

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-teal-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Scenario Studio (V38)</div>
        {validation && (
          <span className={`px-2 py-0.5 rounded text-[8px] ${validation.valid ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
            {validation.valid ? "Valid" : "Invalid"} · {validation.quality_score}/100
          </span>
        )}
      </div>

      <div className="flex gap-2">
        <button onClick={handleLoadExample} className="px-3 py-1.5 rounded bg-teal-500/20 border border-teal-500/30 text-teal-300 hover:bg-teal-500/30">Load Example</button>
        <button onClick={handleValidate} className="px-3 py-1.5 rounded bg-accent/20 border border-accent/30 text-accent-glow hover:bg-accent/30">Validate</button>
        <button onClick={handleImport} disabled={!validation?.valid} className="px-3 py-1.5 rounded bg-green-500/20 border border-green-500/30 text-green-400 hover:bg-green-500/30 disabled:opacity-30">Import</button>
      </div>

      <textarea value={editorText} onChange={e => setEditorText(e.target.value)}
        className="w-full h-32 bg-surface/50 border border-surface-border rounded p-2 text-foreground/60 text-[9px] font-mono resize-y" />

      {validation && (
        <div className="space-y-1 text-[8px]">
          {validation.errors?.length > 0 && <div className="text-red-400">Errors: {validation.errors.join(", ")}</div>}
          {validation.warnings?.length > 0 && <div className="text-amber-400">Warnings: {validation.warnings.join(", ")}</div>}
          {validation.forbidden_terms_found?.length > 0 && <div className="text-red-400 font-bold">Forbidden: {validation.forbidden_terms_found.join(", ")}</div>}
          <div className="flex gap-2">
            <span className={`px-1.5 py-0.5 rounded ${validation.runnable ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>Runnable: {String(validation.runnable)}</span>
            <span className={`px-1.5 py-0.5 rounded ${validation.safe_to_import ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>Safe: {String(validation.safe_to_import)}</span>
          </div>
        </div>
      )}

      <div className="flex gap-2 items-center">
        <input value={scenarioId} onChange={e => setScenarioId(e.target.value)} placeholder="scenario_id" className="px-2 py-1 rounded bg-surface border border-surface-border text-foreground/50 text-[9px] w-40" />
        <button onClick={() => onRunScenario(scenarioId)} disabled={!scenarioId} className="px-3 py-1.5 rounded bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/30 disabled:opacity-30">Run</button>
      </div>

      <div className="text-foreground/20 text-[7px]">{validation?.scientific_boundary}</div>
    </div>
  );
}
