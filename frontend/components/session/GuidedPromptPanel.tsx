"use client";

export default function GuidedPromptPanel({ text }: { text: string }) {
  return (
    <div className="glass p-4 panel-glow">
      <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-accent-glow/80">Guided Cue</div>
      <p className="text-base text-foreground/88 leading-relaxed">
        {text || "Let the corridor settle into a simple, steady outline."}
      </p>
      <p className="mt-2 text-[11px] text-foreground/42">
        Adaptive feedback scaffold. Not decoded mental content.
      </p>
    </div>
  );
}
