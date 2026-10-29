"use client";

import Link from "next/link";
import { useState } from "react";
import BoundaryNote from "@/components/platform/BoundaryNote";
import ClaimBadge from "@/components/platform/ClaimBadge";
import PageHeader from "@/components/platform/PageHeader";
import Panel from "@/components/platform/Panel";
import EvidenceMark from "@/components/evidence/EvidenceMark";
import { downloadText, safeFilename } from "@/lib/preregistration";
import ConsentGate from "./ConsentGate";
import ImagerySelfReportTask, { type SelfReportTrialResult } from "./ImagerySelfReportTask";

const STIMULI = [
  { id: "red_apple", label: "a red apple on a plain wooden table" },
  { id: "harbor_dawn", label: "a quiet harbor at dawn, with one small boat" },
  { id: "glass_stair", label: "a glass staircase turning once to the left" },
];

type Phase = "intro" | "consent" | "trial" | "summary" | "declined";

export default function ParticipantRunner() {
  const [phase, setPhase] = useState<Phase>("intro");
  const [trialIndex, setTrialIndex] = useState(0);
  const [results, setResults] = useState<SelfReportTrialResult[]>([]);
  const [aborted, setAborted] = useState(false);
  const [startedAt, setStartedAt] = useState<string | null>(null);

  const start = () => {
    setResults([]);
    setTrialIndex(0);
    setAborted(false);
    setStartedAt(new Date().toISOString());
    setPhase("trial");
  };

  const completeTrial = (result: SelfReportTrialResult) => {
    setResults((current) => [...current, result]);
    if (trialIndex >= STIMULI.length - 1) {
      setPhase("summary");
    } else {
      setTrialIndex((current) => current + 1);
    }
  };

  const stop = () => {
    setAborted(true);
    setPhase("summary");
  };

  const reset = () => {
    setResults([]);
    setTrialIndex(0);
    setAborted(false);
    setStartedAt(null);
    setPhase("intro");
  };

  const download = () => {
    const payload = {
      schema: "IMAGINA-PARTICIPANT-DEMO-v1",
      generated_at: new Date().toISOString(),
      started_at: startedAt,
      mode: "local-demo",
      live_study: false,
      data_sent: false,
      aborted,
      stimuli: STIMULI,
      trials: results,
      boundaries: [
        "Self-report is subjective and reactive.",
        "No imagery is reconstructed, decoded, or scored objectively.",
        "This demonstration is not a research study, ethics approval, or clinical assessment.",
      ],
    };
    downloadText(
      `${safeFilename("participant-demo")}.json`,
      JSON.stringify(payload, null, 2),
      "application/json",
    );
  };

  return (
    <div className="mx-auto w-full max-w-[1100px] px-4 py-10 md:px-6">
      <PageHeader
        eyebrow="Participant Mode · local demonstration"
        title="Three prompts. Three ratings. Nothing leaves this tab."
        description="A complete participant-facing flow that demonstrates the task, consent, timing, missingness, and export — without pretending to be a live study."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <ClaimBadge />
            <Link
              href="/research/design"
              className="inline-flex h-11 items-center rounded-lg border border-surface-border px-3 text-[11px] text-foreground/60 hover:bg-white/[0.04] hover:text-foreground"
            >
              Study Designer
            </Link>
          </div>
        }
      />

      <div className="mt-6" aria-live="polite">
        {phase === "intro" ? (
          <div className="grid gap-4 md:grid-cols-[1fr_360px]">
            <Panel className="p-6">
              <p className="mono-label text-signal/70">Protocol</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">What happens</h2>
              <ol className="mt-4 space-y-3 text-sm leading-6 text-foreground/60">
                <li>
                  <span className="font-mono text-[11px] text-foreground/35">01</span> You read a local
                  demonstration consent and choose whether to continue.
                </li>
                <li>
                  <span className="font-mono text-[11px] text-foreground/35">02</span> Three trials: a short
                  fixation, an imagery prompt, then three subjective ratings.
                </li>
                <li>
                  <span className="font-mono text-[11px] text-foreground/35">03</span> A local summary with timing,
                  missingness, and a JSON download. No upload.
                </li>
              </ol>
              <div className="mt-5 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setPhase("consent")}
                  className="inline-flex min-h-11 items-center rounded-lg border border-signal/35 bg-signal/[0.09] px-5 text-sm font-medium text-signal hover:bg-signal/[0.14]"
                >
                  Review consent
                </button>
                <Link
                  href="/method"
                  className="inline-flex min-h-11 items-center rounded-lg border border-surface-border px-4 text-sm text-foreground/60 hover:bg-white/[0.04]"
                >
                  Inspect the evidence
                </Link>
              </div>
            </Panel>

            <Panel className="p-5">
              <h2 className="mono-label text-foreground/40">At a glance</h2>
              <dl className="mt-3 space-y-3 text-sm">
                <div>
                  <dt className="text-foreground/40">Trials</dt>
                  <dd className="font-mono text-foreground/80">3</dd>
                </div>
                <div>
                  <dt className="text-foreground/40">Duration</dt>
                  <dd className="font-mono text-foreground/80">~2–4 min</dd>
                </div>
                <div>
                  <dt className="text-foreground/40">Data</dt>
                  <dd className="text-foreground/70">In-memory; optional local JSON</dd>
                </div>
                <div>
                  <dt className="text-foreground/40">Claim ceiling</dt>
                  <dd className="font-mono text-[11px] text-lock/75">L1_BEHAVIORAL_ASSISTED</dd>
                </div>
              </dl>
              <p className="mt-4 border-t border-surface-border pt-3 text-[11px] leading-5 text-foreground/35">
                This is a demonstration protocol, not a live study. It is not ethics approval or a clinical
                assessment.
              </p>
            </Panel>
          </div>
        ) : null}

        {phase === "consent" ? (
          <ConsentGate
            studyTitle="IMAGINA local self-report demonstration"
            consentVersion="demo-1"
            onConsent={start}
            onDecline={() => setPhase("declined")}
          />
        ) : null}

        {phase === "trial" ? (
          <div className="mx-auto max-w-2xl space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-foreground/40">
              <p className="font-mono">
                Trial {trialIndex + 1} / {STIMULI.length}
              </p>
              <p>Stimulus {STIMULI[trialIndex].id}</p>
            </div>
            <ImagerySelfReportTask
              key={`${trialIndex}-${STIMULI[trialIndex].id}`}
              stimulusId={STIMULI[trialIndex].id}
              stimulusLabel={STIMULI[trialIndex].label}
              trialIndex={trialIndex}
              onComplete={completeTrial}
              onAbort={stop}
            />
          </div>
        ) : null}

        {phase === "summary" ? (
          <div className="space-y-4">
            <Panel className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="mono-label text-signal/70">Local summary</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                    {aborted ? "Demonstration stopped early" : "Demonstration complete"}
                  </h2>
                  <p className="mt-1 text-sm text-foreground/50">
                    {results.length} of {STIMULI.length} trials recorded. No data was sent anywhere.
                  </p>
                </div>
                <EvidenceMark evidenceId="selfreport.vividness" />
              </div>

              <div className="mt-5 overflow-x-auto rounded-lg border border-surface-border">
                <table className="w-full min-w-[640px] border-collapse text-left text-xs">
                  <caption className="sr-only">Self-report trial summary</caption>
                  <thead>
                    <tr className="border-b border-surface-border text-foreground/40">
                      <th scope="col" className="px-3 py-2 font-medium">Trial</th>
                      <th scope="col" className="px-3 py-2 font-medium">Stimulus</th>
                      <th scope="col" className="px-3 py-2 font-medium">Vividness</th>
                      <th scope="col" className="px-3 py-2 font-medium">Confidence</th>
                      <th scope="col" className="px-3 py-2 font-medium">Effort</th>
                      <th scope="col" className="px-3 py-2 font-medium">Formation (s)</th>
                      <th scope="col" className="px-3 py-2 font-medium">Rating (s)</th>
                    </tr>
                  </thead>
                  <tbody className="tabular-nums text-foreground/65">
                    {results.map((result) => (
                      <tr key={result.trial_index} className="border-b border-surface-border/60 last:border-0">
                        <td className="px-3 py-2 font-mono">{result.trial_index + 1}</td>
                        <td className="px-3 py-2">{result.stimulus_id}</td>
                        <td className="px-3 py-2">{result.vividness}/7</td>
                        <td className="px-3 py-2">{result.confidence}/7</td>
                        <td className="px-3 py-2">{result.effort}/7</td>
                        <td className="px-3 py-2">{(result.imagery_formation_latency_ms / 1000).toFixed(2)}</td>
                        <td className="px-3 py-2">{(result.rating_completion_latency_ms / 1000).toFixed(2)}</td>
                      </tr>
                    ))}
                    {results.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="px-3 py-6 text-center text-foreground/40">
                          No trials recorded.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>

              <div className="mt-4 grid gap-2 text-[11px] leading-5 text-foreground/40 sm:grid-cols-2">
                <p>Missingness: {STIMULI.length - results.length} trial(s) not recorded.</p>
                <p>Timing is browser-relative and can be affected by tab throttling.</p>
              </div>

              <div className="mt-5 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={download}
                  disabled={results.length === 0}
                  className="inline-flex min-h-11 items-center rounded-lg border border-signal/35 bg-signal/[0.09] px-4 text-sm text-signal hover:bg-signal/[0.14] disabled:opacity-40"
                >
                  Download local JSON
                </button>
                <button
                  type="button"
                  onClick={reset}
                  className="inline-flex min-h-11 items-center rounded-lg border border-surface-border px-4 text-sm text-foreground/60 hover:bg-white/[0.04]"
                >
                  Start over
                </button>
                <Link
                  href="/research/design"
                  className="inline-flex min-h-11 items-center rounded-lg border border-surface-border px-4 text-sm text-foreground/60 hover:bg-white/[0.04]"
                >
                  Design a real plan
                </Link>
              </div>
            </Panel>

            <BoundaryNote>
              These are subjective self-report ratings from a local demonstration. They do not measure imagery
              objectively, establish an effect, or support a clinical claim.
            </BoundaryNote>
          </div>
        ) : null}

        {phase === "declined" ? (
          <Panel className="mx-auto max-w-xl p-6 text-center">
            <h2 className="text-xl font-semibold">Demonstration not started</h2>
            <p className="mt-2 text-sm leading-6 text-foreground/55">
              No ratings were collected. You can review the method or return to the research platform.
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              <button
                type="button"
                onClick={reset}
                className="inline-flex min-h-11 items-center rounded-lg border border-surface-border px-4 text-sm text-foreground/60 hover:bg-white/[0.04]"
              >
                Back to start
              </button>
              <Link
                href="/research"
                className="inline-flex min-h-11 items-center rounded-lg border border-surface-border px-4 text-sm text-foreground/60 hover:bg-white/[0.04]"
              >
                Research platform
              </Link>
            </div>
          </Panel>
        ) : null}
      </div>

      <div className="mt-8">
        <BoundaryNote>
          Participant Mode is a local demonstration. It is not a live study, does not persist data, and is not a
          substitute for ethics review or clinical care.
        </BoundaryNote>
      </div>
    </div>
  );
}
