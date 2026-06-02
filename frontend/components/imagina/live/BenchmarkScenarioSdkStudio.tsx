"use client";

import { useState, useEffect } from "react";

interface GalleryTemplate { scenario_id: string; title: string; purpose: string; payload: Record<string, unknown>; }
interface ValidResult { valid: boolean; quality_score: number; safe_to_import: boolean; runnable: boolean; warnings: string[]; errors: string[]; forbidden_terms_found: string[]; scientific_boundary?: string; }
interface ImportedScenario { scenario_id: string; payload?: { title?: string }; valid?: boolean; }
interface CustomSuite { suite_id: string; suite_name: string; scenario_ids: string[]; }

interface SDSProps {
  userId?: string;
  onGetSchema: () => Promise<unknown>;
  onGetExample: () => Promise<Record<string, unknown>>;
  onValidate: (payload: Record<string, unknown>) => Promise<ValidResult | null>;
  onImport: (payload: Record<string, unknown>) => Promise<unknown>;
  onRunImported: (sid: string) => Promise<unknown>;
  onRunSuite: (sid: string) => Promise<unknown>;
  onExportSdk: () => Promise<unknown>;
  onListImported: () => Promise<ImportedScenario[]>;
  onListSuites: () => Promise<CustomSuite[]>;
}

export function BenchmarkScenarioSdkStudio({
  userId, onGetExample, onValidate, onImport, onRunImported, onRunSuite, onExportSdk, onListImported, onListSuites,
}: SDSProps) {
  return (
    <div className="space-y-3 text-[10px] border-l-2 border-teal-500/50 pl-2">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Benchmark Scenario SDK Studio (V39)</div>
      <div className="text-foreground/30 text-[9px]">
        Scenario SDK: Validate → Import → Run → Suite → Export. External scenarios test symbolic scene adaptation only.
        <span className="px-1.5 py-0.5 ml-1 rounded bg-cyan-500/20 text-cyan-400 text-[7px]">raw_eeg: false</span>
        <span className="px-1.5 py-0.5 ml-1 rounded bg-green-500/20 text-green-400 text-[7px]">not BCI</span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <SimpleScenarioStudioPanel onGetExample={onGetExample} onValidate={onValidate} onImport={onImport} onRunImported={onRunImported} />
        <SimpleImportedPanel onListImported={onListImported} onRunImported={onRunImported} onRefresh={() => {}} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <SimpleSuitePanel onListSuites={onListSuites} onRunSuite={onRunSuite} onRefresh={() => {}} />
        <SimpleExportPanel onExport={onExportSdk} />
      </div>
    </div>
  );
}

function SimpleScenarioStudioPanel({ onGetExample, onValidate, onImport, onRunImported }: {
  onGetExample: () => Promise<Record<string, unknown>>; onValidate: (p: Record<string, unknown>) => Promise<ValidResult | null>;
  onImport: (p: Record<string, unknown>) => Promise<unknown>; onRunImported: (sid: string) => Promise<unknown>;
}) {
  const [text, setText] = useState("{}");
  const [val, setVal] = useState<ValidResult | null>(null);
  const [sid, setSid] = useState("");

  return (
    <div className="glass p-3 space-y-2">
      <div className="flex justify-between"><div className="text-foreground/40 text-[9px]">JSON Editor</div>
        {val && <span className={`text-[8px] ${val.valid ? "text-green-400" : "text-red-400"}`}>{val.valid ? "Valid" : "Invalid"} · {val.quality_score}</span>}
      </div>
      <textarea value={text} onChange={e => setText(e.target.value)} className="w-full h-24 bg-surface/50 border border-surface-border rounded p-1 text-foreground/60 text-[8px] font-mono resize-y" />
      <div className="flex gap-1">
        <button onClick={async () => { const ex = await onGetExample(); setText(JSON.stringify(ex, null, 2)); }} className="px-2 py-1 rounded bg-teal-500/20 border border-teal-500/30 text-teal-300 text-[8px]">Example</button>
        <button onClick={async () => { try { setVal(await onValidate(JSON.parse(text))); } catch { setVal({ valid: false, quality_score: 0, safe_to_import: false, runnable: false, warnings: [], errors: ["Invalid JSON"], forbidden_terms_found: [] } as ValidResult); } }} className="px-2 py-1 rounded bg-accent/20 border border-accent/30 text-accent-glow text-[8px]">Validate</button>
        <button onClick={async () => { await onImport(JSON.parse(text)); }} disabled={!val?.valid} className="px-2 py-1 rounded bg-green-500/20 border border-green-500/30 text-green-400 text-[8px] disabled:opacity-30">Import</button>
      </div>
      <div className="flex gap-1">
        <input value={sid} onChange={e => setSid(e.target.value)} placeholder="scenario_id" className="px-1 py-0.5 rounded bg-surface border text-foreground/50 text-[8px] w-32" />
        <button onClick={() => onRunImported(sid)} className="px-2 py-1 rounded bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 text-[8px]">Run</button>
      </div>
      {(val?.forbidden_terms_found?.length ?? 0) > 0 && <div className="text-red-400 text-[7px]">Forbidden: {val?.forbidden_terms_found?.join(", ")}</div>}
    </div>
  );
}

function SimpleImportedPanel({ onListImported, onRunImported, onRefresh }: {
  onListImported: () => Promise<ImportedScenario[]>; onRunImported: (sid: string) => Promise<unknown>; onRefresh: () => void;
}) {
  const [scenarios, setScenarios] = useState<ImportedScenario[]>([]);
  useEffect(() => { onListImported().then(setScenarios); }, [onListImported]);
  return (
    <div className="glass p-3 space-y-2">
      <div className="flex justify-between"><div className="text-foreground/40 text-[9px]">Imported ({scenarios.length})</div></div>
      <div className="space-y-1 max-h-24 overflow-y-auto">
        {scenarios.slice(0, 5).map(s => (
          <div key={s.scenario_id} className="flex gap-1 text-[8px]">
            <span className="text-foreground/60 flex-1 truncate">{s.payload?.title || s.scenario_id || "—"}</span>
            <button onClick={() => onRunImported(s.scenario_id)} className="px-1.5 py-0.5 rounded bg-indigo-500/20 border border-indigo-500/30 text-indigo-300">Run</button>
          </div>
        ))}
      </div>
    </div>
  );
}

function SimpleSuitePanel({ onListSuites, onRunSuite, onRefresh }: {
  onListSuites: () => Promise<CustomSuite[]>; onRunSuite: (sid: string) => Promise<unknown>; onRefresh: () => void;
}) {
  const [suites, setSuites] = useState<CustomSuite[]>([]);
  useEffect(() => { onListSuites().then(setSuites); }, [onListSuites]);
  return (
    <div className="glass p-3 space-y-2">
      <div className="flex justify-between"><div className="text-foreground/40 text-[9px]">Suites ({suites.length})</div></div>
      {suites.slice(0, 3).map(s => (
        <div key={s.suite_id} className="flex gap-1 text-[8px]">
          <span className="text-foreground/60 flex-1 truncate">{s.suite_name}</span>
          <button onClick={() => onRunSuite(s.suite_id)} className="px-1.5 py-0.5 rounded bg-emerald-500/20 border border-emerald-500/30 text-emerald-300">Run</button>
        </div>
      ))}
    </div>
  );
}

function SimpleExportPanel({ onExport }: { onExport: () => Promise<unknown> }) {
  return (
    <div className="glass p-3 space-y-2">
      <div className="text-foreground/40 text-[9px]">SDK Export</div>
      <button onClick={onExport} className="px-2 py-1 rounded bg-violet-500/20 border border-violet-500/30 text-violet-300 text-[8px]">Export SDK Pack</button>
      <div className="text-foreground/30 text-[7px]">Schemas, scenarios, suite summaries, safety boundaries. No raw EEG.</div>
    </div>
  );
}
