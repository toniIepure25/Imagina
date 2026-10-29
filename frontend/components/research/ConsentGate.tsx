"use client";

import { useState } from "react";

interface ConsentGateProps {
  studyTitle: string;
  consentVersion: string;
  onConsent: () => void;
  onDecline: () => void;
}

const SECTIONS = [
  {
    title: "What this is",
    body: "A local demonstration of a self-report imagery task. It runs entirely in this browser tab and is not a live research study.",
  },
  {
    title: "What you will do",
    body: "You will see three short imagery prompts, spend a few seconds imagining each one, and rate vividness, confidence, and effort.",
  },
  {
    title: "Data",
    body: "No ratings are saved by the platform and nothing is sent to a server. You can download a local JSON summary only if you choose to.",
  },
  {
    title: "Risks and stopping",
    body: "Imagery can be tiring. You may stop at any time. This demonstration is not therapy, diagnosis, or clinical care.",
  },
  {
    title: "What it cannot show",
    body: "It cannot measure imagery objectively, read your mind, decode a dream, or establish that any practice works.",
  },
];

export default function ConsentGate({ studyTitle, consentVersion, onConsent, onDecline }: ConsentGateProps) {
  const [accepted, setAccepted] = useState(false);

  return (
    <section className="mx-auto max-w-2xl rounded-xl border border-surface-border bg-white/[0.025] p-6 sm:p-8">
      <p className="mono-label text-lock/70">Local demonstration consent</p>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight">Before you begin</h2>
      <p className="mt-2 text-sm leading-6 text-foreground/55">
        {studyTitle} · demo version {consentVersion}
      </p>

      <div className="mt-5 space-y-3">
        {SECTIONS.map((section) => (
          <div key={section.title} className="rounded-lg border border-surface-border bg-white/[0.02] p-4">
            <h3 className="text-sm font-semibold text-foreground/80">{section.title}</h3>
            <p className="mt-1 text-sm leading-6 text-foreground/55">{section.body}</p>
          </div>
        ))}
      </div>

      <label className="mt-5 flex cursor-pointer items-start gap-3 rounded-lg border border-surface-border p-3">
        <input
          type="checkbox"
          checked={accepted}
          onChange={(event) => setAccepted(event.target.checked)}
          className="mt-0.5 h-5 w-5 shrink-0 accent-[var(--signal)]"
        />
        <span className="text-sm leading-6 text-foreground/65">
          I understand this is a local demonstration, not a research study or ethics-approved protocol.
        </span>
      </label>

      <div className="mt-5 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onConsent}
          disabled={!accepted}
          className="inline-flex min-h-11 items-center rounded-lg border border-signal/35 bg-signal/[0.09] px-5 text-sm font-medium text-signal hover:bg-signal/[0.14] disabled:cursor-not-allowed disabled:opacity-40"
        >
          Start demonstration
        </button>
        <button
          type="button"
          onClick={onDecline}
          className="inline-flex min-h-11 items-center rounded-lg border border-surface-border px-5 text-sm text-foreground/60 hover:bg-white/[0.04]"
        >
          Exit
        </button>
      </div>
    </section>
  );
}
