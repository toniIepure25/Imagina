"use client";

import { useState } from "react";

interface PPStudioProps {
  onValidate: (p: Record<string, unknown>) => Promise<Record<string, unknown>>;
  onImport: (p: Record<string, unknown>) => Promise<unknown>;
  onRun: (pid: string) => void;
  onGetExample: () => Promise<Record<string, unknown>>;
}

export function PolicyProfileStudioPanel({ onValidate, onImport, onRun, onGetExample }: PPStudioProps) {
  const [text, setText] = useState("{}");
  const [val, setVal] = useState<Record<string, unknown> | null>(null);
  const [pid, setPid] = useState("");
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-fuchsia-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Policy Studio (V41)</div>
      <textarea value={text} onChange={e => setText(e.target.value)} className="w-full h-24 bg-surface/50 border border-surface-border rounded p-2 text-foreground/60 text-[9px] font-mono" />
      <div className="flex gap-1">
        <button onClick={async () => { setText(JSON.stringify(await onGetExample(), null, 2)); }} className="px-2 py-1 rounded bg-fuchsia-500/20 border border-fuchsia-500/30 text-fuchsia-300 text-[8px]">Example</button>
        <button onClick={async () => { try { setVal(await onValidate(JSON.parse(text))); } catch { setVal({ valid: false, quality_score: 0 } as unknown as Record<string, unknown>); } }} className="px-2 py-1 rounded bg-accent/20 border border-accent/30 text-accent-glow text-[8px]">Validate</button>
        <button onClick={() => onImport(JSON.parse(text))} disabled={!val?.valid} className="px-2 py-1 rounded bg-green-500/20 border border-green-500/30 text-green-400 text-[8px] disabled:opacity-30">Import</button>
      </div>
      <input value={pid} onChange={e => setPid(e.target.value)} placeholder="policy_id" className="px-1 py-0.5 rounded bg-surface border text-foreground/50 text-[8px] w-32" />
      <button onClick={() => onRun(pid)} className="px-2 py-1 rounded bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 text-[8px]">Run Benchmark</button>
    </div>
  );
}
