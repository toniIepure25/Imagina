"use client";

interface BuiltinProtocol { template_id: string; title: string; description: string; duration_days: number; protocol_type: string; }
interface ProtocolRun { run_id: string; protocol_title: string; status: string; progress: { completed_blocks: number; total_blocks: number; completion_rate: number }; active_session_id: string | null; }

interface PSPProps { builtin: BuiltinProtocol[]; protocols: BuiltinProtocol[]; activeRun: ProtocolRun | null; onInstantiate: (tid: string) => void; onStartRun: (pid: string) => void; onStartBlock: () => void; onCompleteBlock: (sid: string) => void; onRefresh: () => void; }

export function ImageryProtocolStudioPanel({ builtin, protocols, activeRun, onInstantiate, onStartRun, onStartBlock, onCompleteBlock, onRefresh }: PSPProps) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-amber-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Protocol Studio (V23)</div>
      {activeRun ? (
        <div className="p-2 rounded bg-green-500/10 space-y-1">
          <div className="text-foreground/60">{activeRun.protocol_title}</div>
          <div className="flex gap-1 text-[9px]">
            <span className="text-green-400">{activeRun.status}</span>
            <span className="text-foreground/30">{activeRun.progress.completed_blocks}/{activeRun.progress.total_blocks} blocks ({ (activeRun.progress.completion_rate * 100).toFixed(0)}%)</span>
          </div>
          <div className="flex gap-1">
            {activeRun.active_session_id ? (
              <button onClick={() => onCompleteBlock(activeRun.active_session_id!)} className="px-2 py-1 rounded bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-[9px]">Complete Block</button>
            ) : (
              <button onClick={onStartBlock} className="px-2 py-1 rounded bg-amber-500/20 border border-amber-500/30 text-amber-300 text-[9px]">Start Next Block</button>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-1 max-h-40 overflow-y-auto">
          {builtin?.slice(0, 4).map(bp => (
            <div key={bp.template_id} className="flex gap-2 text-[8px] p-1.5 rounded bg-surface/30 items-center">
              <span className="text-foreground/60 flex-1 truncate">{bp.title}</span>
              <span className="text-foreground/30">{bp.duration_days}d</span>
              <button onClick={() => onInstantiate(bp.template_id)} className="px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/30 text-amber-300 hover:bg-amber-500/30">Use</button>
            </div>
          ))}
        </div>
      )}
      <button onClick={onRefresh} className="px-2 py-1 rounded bg-surface border border-surface-border text-foreground/50 text-[9px]">Refresh</button>
    </div>
  );
}
