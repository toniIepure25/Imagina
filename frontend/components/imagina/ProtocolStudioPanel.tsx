"use client";

interface DesignTemplate {
  id: string; name: string; hypothesis: string;
  design_type: string; planned_n_sessions: number;
}

interface ValidationResult {
  valid: boolean; quality_score: number; confidence_level: string;
  warnings: string[]; errors: string[];
}

export function ProtocolStudioPanel({
  onSelectTemplate, onCreateDesign, onValidate, onCompile,
  templates, designs, validation, compiled
}: {
  onSelectTemplate: (id: string) => void;
  onCreateDesign: () => void;
  onValidate: () => void;
  onCompile: () => void;
  templates: DesignTemplate[];
  designs: { design_id: string; name: string; hypothesis: string }[] | null;
  validation: ValidationResult | null;
  compiled: { protocol_id?: string } | null;
}) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-violet-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Protocol Studio</div>

      {/* Templates */}
      <div>
        <div className="text-foreground/50 mb-2">Design Templates</div>
        <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">
          {templates.slice(0, 6).map(t => (
            <button key={t.id} onClick={() => onSelectTemplate(t.id)}
                    className="text-left p-2 rounded bg-surface/50 border border-surface-border hover:bg-surface/70 text-[9px]">
              <div className="text-foreground">{t.name}</div>
              <div className="text-foreground/40">{t.planned_n_sessions} sessions · {t.design_type}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button onClick={onCreateDesign}
                className="px-3 py-1.5 rounded bg-accent/20 border border-accent/30 text-accent-glow hover:bg-accent/30">
          Create Design
        </button>
        <button onClick={onValidate}
                className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Validate
        </button>
        <button onClick={onCompile}
                className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">
          Compile
        </button>
      </div>

      {/* Validation */}
      {validation && (
        <div className="p-2 rounded bg-surface/30 space-y-1">
          <div className="flex gap-2 items-center">
            <span className={validation.valid ? "text-green-400" : "text-red-400"}>
              {validation.valid ? "✓" : "✗"}
            </span>
            <span>Score: {validation.quality_score}/100 · {validation.confidence_level} confidence</span>
          </div>
          {validation.warnings.map((w, i) => (
            <div key={i} className="text-amber-400/70 text-[9px]">⚠ {w}</div>
          ))}
          {validation.errors.map((e, i) => (
            <div key={i} className="text-red-400/70 text-[9px]">✗ {e}</div>
          ))}
        </div>
      )}

      {/* Compilation */}
      {compiled?.protocol_id && (
        <div className="p-2 rounded bg-green-500/10 border border-green-500/20 text-[9px] text-green-400">
          ✓ Protocol compiled: {compiled.protocol_id?.slice(0, 8)}...
        </div>
      )}

      {/* Designs list */}
      {designs && designs.length > 0 && (
        <div className="text-foreground/40 text-[9px]">
          {designs.length} saved design(s)
        </div>
      )}
    </div>
  );
}
