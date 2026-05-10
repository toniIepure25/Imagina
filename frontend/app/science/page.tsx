import AppShell from "@/components/layout/AppShell";

const LIMITS = [
  "V1 uses simulated EEG-like signals, not real neural data.",
  "Self-report is subjective and may not reflect actual imagery quality.",
  "PID and IQI are experimental composite proxy metrics.",
  "The scene is feedback scaffolding, not reconstruction of mental images.",
  "Results are not clinical evaluation and should not guide medical decisions.",
];

export default function SciencePage() {
  return (
    <AppShell>
      <div className="flex-1 mx-auto w-full max-w-5xl px-6 py-14 space-y-8">
        <div className="space-y-3">
          <div className="text-[11px] uppercase tracking-[0.24em] text-accent-glow/70">Scientific Framing</div>
          <h1 className="text-4xl font-bold glow-text">How IMAGINA V2 Should Be Interpreted</h1>
          <p className="max-w-3xl text-sm leading-7 text-foreground/62">
            IMAGINA V2 is a simulated, local-first closed-loop prototype. It estimates experimental proxy metrics
            from self-report, behavioral-style features, and simulated EEG-like signals, then adapts a procedural
            corridor as feedback.
          </p>
        </div>

        <section className="grid gap-4 md:grid-cols-2">
          <div className="glass panel-glow p-6">
            <h2 className="text-lg font-semibold text-accent-glow">IQI Proxy</h2>
            <p className="mt-3 text-sm leading-7 text-foreground/65">
              IQI combines attention stability, imagery engagement, behavioral consistency, relaxation, and confidence.
              Higher values indicate a stronger estimated imagery-quality proxy, not a direct measurement of imagery.
            </p>
          </div>
          <div className="glass panel-glow p-6">
            <h2 className="text-lg font-semibold text-yellow-300">PID Proxy</h2>
            <p className="mt-3 text-sm leading-7 text-foreground/65">
              PID estimates a distance-like proxy from simulated neural features, behavioral distance, and uncertainty.
              Lower values are treated as better alignment with the target practice state.
            </p>
          </div>
        </section>

        <section className="glass panel-glow p-6">
          <h2 className="text-lg font-semibold text-accent-glow">Closed-loop Feedback</h2>
          <p className="mt-3 text-sm leading-7 text-foreground/65">
            Feedback changes the corridor clarity, fog, wall distortion, lights, particles, doors, and breathing pulse.
            The corridor is not a decoded mental image. It is an adaptive scaffold driven by experimental proxy metrics.
          </p>
        </section>

        <section className="grid gap-4 lg:grid-cols-[1fr_1fr]">
          <div className="glass panel-glow p-6">
            <h2 className="text-lg font-semibold text-danger">Limitations</h2>
            <ul className="mt-3 space-y-2 text-sm text-foreground/65">
              {LIMITS.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div className="glass panel-glow p-6">
            <h2 className="text-lg font-semibold text-accent-glow">Future Validation</h2>
            <div className="mt-3 space-y-3 text-sm leading-7 text-foreground/65">
              <p>V2 may integrate real EEG through LSL streams such as Muse or OpenBCI, with artifact-aware preprocessing.</p>
              <p>V3 may explore learned representation models only after validation against controlled psychophysical measures.</p>
              <p>Any future claims should be supported by formal experiments, transparent methods, and appropriate limitations.</p>
            </div>
          </div>
        </section>

        <div className="text-center text-xs text-foreground/35">
          IMAGINA does not read minds, decode dreams, diagnose, treat, or measure consciousness objectively.
        </div>
      </div>
    </AppShell>
  );
}
