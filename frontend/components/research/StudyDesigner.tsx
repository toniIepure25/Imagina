"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import ClaimBadge from "@/components/platform/ClaimBadge";
import PageHeader from "@/components/platform/PageHeader";
import Panel from "@/components/platform/Panel";
import BoundaryNote from "@/components/platform/BoundaryNote";
import EvidenceMark from "@/components/evidence/EvidenceMark";
import GlassBoxToggle from "@/components/evidence/GlassBoxToggle";
import { getEvidence, studyEligibleEvidence } from "@/lib/evidence/registry";
import { buildRandomizationPreview } from "@/lib/randomization";
import {
  MODE_CEILING,
  STUDY_APP_VERSION,
  createDefaultDesign,
  planningHalfWidth,
  totalSessions,
  validateStudyDesign,
  withLock,
  withNewRevision,
  type StudyAnalysis,
  type StudyDesign,
  type StudyMode,
  type StudyShape,
} from "@/lib/studyDesign";
import { buildPlanExport, downloadText, hashStudyDesign, safeFilename, type ExportedPlan } from "@/lib/preregistration";

const DRAFT_KEY = "imagina.studyDraft.v1";
const STEPS = ["Scope", "Measures", "Design", "Analysis", "Review & export"] as const;

const MODES: Array<{ id: StudyMode; label: string; description: string }> = [
  {
    id: "explore",
    label: "Explore",
    description: "Hypothesis-generating only. No confirmatory p-values.",
  },
  {
    id: "personal",
    label: "Personal N-of-1",
    description: "A descriptive case plan, or a randomization test when the plan is fixed first.",
  },
  {
    id: "research",
    label: "Research-grade",
    description: "Requires external protocol review and ethics approval before collection.",
  },
];

const SHAPES: StudyShape[] = ["immediate", "gradual", "delayed", "temporary"];

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mono-label text-foreground/45">{label}</span>
      {children}
      {hint ? <span className="mt-1 block text-[11px] leading-5 text-foreground/35">{hint}</span> : null}
    </label>
  );
}

export default function StudyDesigner() {
  const searchParams = useSearchParams();
  const [design, setDesign] = useState<StudyDesign>(() => createDefaultDesign());
  const [step, setStep] = useState(0);
  const [hash, setHash] = useState<string | null>(null);
  const [exported, setExported] = useState<ExportedPlan | null>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const eligible = useMemo(() => studyEligibleEvidence(), []);
  const eligibleIds = useMemo(() => new Set(eligible.map((entry) => entry.id)), [eligible]);
  const validation = useMemo(() => validateStudyDesign(design, eligibleIds), [design, eligibleIds]);
  const preview = useMemo(
    () =>
      buildRandomizationPreview({
        seed: design.seed,
        blocks: design.blocks,
        blockLength: design.blockLength,
        scheme: design.randomization,
      }),
    [design.blockLength, design.blocks, design.randomization, design.seed],
  );
  const halfWidth = planningHalfWidth(design.planningSd, design.blocks * design.blockLength);
  const sourceEvidence = getEvidence(searchParams.get("from"));
  const primaryEvidence = getEvidence(design.primaryOutcome);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        const raw = window.sessionStorage.getItem(DRAFT_KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as Partial<StudyDesign>;
          const base = createDefaultDesign();
          setDesign({
            ...base,
            ...parsed,
            analysis: { ...base.analysis, ...(parsed.analysis ?? {}) },
            conditions: { ...base.conditions, ...(parsed.conditions ?? {}) },
            boundaries: parsed.boundaries ?? base.boundaries,
          });
        }
      } catch {
        // A malformed local draft is ignored rather than trusted.
      }
      const from = searchParams.get("from");
      const entry = getEvidence(from);
      if (entry?.studyEligible) {
        setDesign((current) => ({
          ...current,
          primaryOutcome: entry.id,
          question:
            current.question ||
            `In this case, does ${entry.label.toLowerCase()} change in the expected direction under the practice condition?`,
        }));
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, [searchParams]);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(DRAFT_KEY, JSON.stringify(design));
    } catch {
      // Draft persistence is optional.
    }
  }, [design]);

  const update = (patch: Partial<StudyDesign>) => {
    setDesign((current) => ({ ...current, ...patch }));
    setHash(null);
    setExported(null);
    setNotice("");
  };

  const updateAnalysis = (patch: Partial<StudyAnalysis>) => {
    setDesign((current) => ({ ...current, analysis: { ...current.analysis, ...patch } }));
    setHash(null);
    setExported(null);
    setNotice("");
  };

  const toggleSecondary = (id: string) => {
    const next = design.secondaryOutcomes.includes(id)
      ? design.secondaryOutcomes.filter((item) => item !== id)
      : [...design.secondaryOutcomes, id];
    update({ secondaryOutcomes: next });
  };

  const resetDraft = () => {
    const next = createDefaultDesign();
    setDesign(next);
    setHash(null);
    setExported(null);
    setStep(0);
    setNotice("Draft reset.");
    try {
      window.sessionStorage.removeItem(DRAFT_KEY);
    } catch {
      // Ignore.
    }
  };

  const lockPlan = async () => {
    if (!validation.readyToLock) {
      setNotice("Resolve the blocking errors before locking.");
      setStep(3);
      return;
    }
    setBusy(true);
    const locked = withLock(design);
    const nextHash = await hashStudyDesign(locked);
    const nextExport = buildPlanExport(locked, nextHash);
    setDesign(locked);
    setHash(nextHash);
    setExported(nextExport);
    setStep(4);
    setBusy(false);
    setNotice(
      nextHash
        ? `Plan locked · revision ${locked.revision} · SHA-256 ${nextHash.slice(0, 12)}…`
        : "Plan locked without a hash. Web Crypto is unavailable in this browser.",
    );
  };

  const newRevision = () => {
    setDesign((current) => withNewRevision(current));
    setHash(null);
    setExported(null);
    setStep(0);
    setNotice("New revision opened. Previous lock remains in the exported artifact.");
  };

  const download = (kind: "json" | "md") => {
    const plan = exported ?? buildPlanExport(design, hash);
    if (!plan.plan.lockedAt) {
      setNotice("Lock the plan before exporting.");
      return;
    }
    const base = safeFilename(design.title);
    if (kind === "json") {
      downloadText(`${base}.json`, plan.json, "application/json");
    } else {
      downloadText(`${base}.md`, plan.markdown, "text/markdown");
    }
    setNotice(`${kind.toUpperCase()} downloaded locally.`);
  };

  const copyMarkdown = async () => {
    const plan = exported ?? buildPlanExport(design, hash);
    if (!plan.plan.lockedAt) {
      setNotice("Lock the plan before copying.");
      return;
    }
    try {
      await navigator.clipboard.writeText(plan.markdown);
      setNotice("Markdown copied to the clipboard.");
    } catch {
      setNotice("Clipboard unavailable. Use Download Markdown instead.");
    }
  };

  return (
    <div className="mx-auto w-full max-w-[1320px] px-4 py-10 md:px-6">
      <PageHeader
        eyebrow="Falsification Studio"
        title="Design the test before you see the data."
        description="A local N-of-1 planner with a lock, version, hash, and explicit boundaries. It produces a plan, not a result, a p-value, or ethics approval."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <ClaimBadge />
            <GlassBoxToggle />
            <button
              type="button"
              onClick={resetDraft}
              className="inline-flex h-11 items-center rounded-lg border border-surface-border px-3 text-[11px] text-foreground/60 hover:bg-white/[0.04] hover:text-foreground"
            >
              Reset draft
            </button>
          </div>
        }
      />

      <div className="mt-6 flex flex-wrap items-center gap-2" aria-label="Design steps">
        {STEPS.map((label, index) => (
          <button
            key={label}
            type="button"
            onClick={() => setStep(index)}
            aria-current={step === index ? "step" : undefined}
            className={`inline-flex min-h-10 items-center gap-2 rounded-lg border px-3 text-[11px] transition-colors ${
              step === index
                ? "border-signal/35 bg-signal/[0.08] text-signal"
                : "border-surface-border text-foreground/45 hover:bg-white/[0.04] hover:text-foreground/70"
            }`}
          >
            <span className="font-mono">{index + 1}</span>
            {label}
          </button>
        ))}
      </div>

      {design.lockedAt ? (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-lock/30 bg-lock/[0.06] px-4 py-3">
          <p className="text-sm text-lock">
            Locked revision {design.revision} · {design.lockedAt}
          </p>
          <button
            type="button"
            onClick={newRevision}
            className="inline-flex min-h-10 items-center rounded-lg border border-lock/35 px-3 text-[11px] text-lock hover:bg-lock/[0.1]"
          >
            Create a new revision
          </button>
        </div>
      ) : null}

      {notice ? (
        <p role="status" aria-live="polite" className="mt-4 rounded-lg border border-surface-border bg-white/[0.03] px-3 py-2 text-xs text-foreground/60">
          {notice}
        </p>
      ) : null}

      <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_340px]">
        <div className="space-y-4">
          {step === 0 ? (
            <Panel className="p-5">
              <h2 className="text-base font-semibold">Scope the claim</h2>
              <p className="mt-1 text-sm leading-6 text-foreground/50">
                The mode sets the ceiling shown on every later screen. It cannot be raised by exporting the plan.
              </p>
              <div className="mt-4 grid gap-2 sm:grid-cols-3">
                {MODES.map((mode) => (
                  <button
                    key={mode.id}
                    type="button"
                    onClick={() => update({ mode: mode.id })}
                    disabled={Boolean(design.lockedAt)}
                    className={`rounded-lg border p-3 text-left transition-colors ${
                      design.mode === mode.id
                        ? "border-signal/35 bg-signal/[0.07]"
                        : "border-surface-border hover:bg-white/[0.035]"
                    } disabled:opacity-60`}
                  >
                    <span className="block text-sm font-medium text-foreground/85">{mode.label}</span>
                    <span className="mt-1 block text-[11px] leading-5 text-foreground/45">{mode.description}</span>
                  </button>
                ))}
              </div>
              <p className="mt-3 rounded-lg border border-lock/25 bg-lock/[0.05] p-3 text-xs leading-5 text-lock/80">
                {MODE_CEILING[design.mode]}
              </p>

              {sourceEvidence ? (
                <div className="mt-4 flex items-start gap-2 rounded-lg border border-signal/25 bg-signal/[0.05] p-3">
                  <EvidenceMark evidenceId={sourceEvidence.id} />
                  <div>
                    <p className="text-xs text-signal">Based on claim: {sourceEvidence.label}</p>
                    <p className="mt-1 text-[11px] leading-5 text-foreground/50">
                      This plan tests a hypothesis. It does not validate the claim.
                    </p>
                  </div>
                </div>
              ) : null}

              <div className="mt-5 space-y-4">
                <Field label="Plan title">
                  <input
                    value={design.title}
                    onChange={(event) => update({ title: event.target.value })}
                    disabled={Boolean(design.lockedAt)}
                    placeholder="Vividness under guided practice: a personal N-of-1 plan"
                    className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none placeholder:text-foreground/25 focus:border-signal/40 disabled:opacity-60"
                  />
                </Field>
                <Field label="Question" hint="State a directional, falsifiable question about this case.">
                  <textarea
                    value={design.question}
                    onChange={(event) => update({ question: event.target.value })}
                    disabled={Boolean(design.lockedAt)}
                    rows={4}
                    placeholder="In this case, does guided imagery practice change self-reported vividness relative to rest?"
                    className="mt-1 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 py-2 text-sm leading-6 outline-none placeholder:text-foreground/25 focus:border-signal/40 disabled:opacity-60"
                  />
                </Field>
              </div>
            </Panel>
          ) : null}

          {step === 1 ? (
            <Panel className="p-5">
              <h2 className="text-base font-semibold">Choose one primary measure</h2>
              <p className="mt-1 text-sm leading-6 text-foreground/50">
                One outcome, one contrast, one decision. Secondary outcomes stay descriptive.
              </p>
              <div className="mt-4 space-y-4">
                <Field label="Primary outcome">
                  <div className="mt-1 flex items-center gap-2">
                    <select
                      value={design.primaryOutcome}
                      onChange={(event) => update({ primaryOutcome: event.target.value })}
                      disabled={Boolean(design.lockedAt)}
                      className="h-11 min-w-0 flex-1 rounded-lg border border-surface-border bg-[#090b14] px-3 text-sm text-foreground/75 disabled:opacity-60"
                    >
                      {eligible.map((entry) => (
                        <option key={entry.id} value={entry.id}>
                          {entry.label} · {entry.id}
                        </option>
                      ))}
                    </select>
                    <EvidenceMark evidenceId={design.primaryOutcome} />
                  </div>
                  <span className="mt-2 block text-[11px] leading-5 text-lock/70">
                    {primaryEvidence?.cannot ?? "Unregistered outcome."}
                  </span>
                </Field>

                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Expected direction">
                    <select
                      value={design.direction}
                      onChange={(event) => update({ direction: event.target.value as StudyDesign["direction"] })}
                      disabled={Boolean(design.lockedAt)}
                      className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-[#090b14] px-3 text-sm text-foreground/75 disabled:opacity-60"
                    >
                      <option value="increase">Increase</option>
                      <option value="decrease">Decrease</option>
                    </select>
                  </Field>
                  <Field label="Minimum meaningful change">
                    <input
                      type="number"
                      min={0.1}
                      step={0.1}
                      value={design.minimumMeaningfulChange}
                      onChange={(event) => update({ minimumMeaningfulChange: Number(event.target.value) })}
                      disabled={Boolean(design.lockedAt)}
                      className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none focus:border-signal/40 disabled:opacity-60"
                    />
                  </Field>
                </div>

                <div>
                  <p className="mono-label text-foreground/45">Secondary outcomes · exploratory</p>
                  <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
                    {eligible
                      .filter((entry) => entry.id !== design.primaryOutcome)
                      .map((entry) => (
                        <label
                          key={entry.id}
                          className="flex min-h-10 items-center gap-2 rounded-lg border border-surface-border px-3 text-xs text-foreground/60"
                        >
                          <input
                            type="checkbox"
                            checked={design.secondaryOutcomes.includes(entry.id)}
                            onChange={() => toggleSecondary(entry.id)}
                            disabled={Boolean(design.lockedAt)}
                            className="h-4 w-4 accent-[var(--signal)]"
                          />
                          {entry.label}
                        </label>
                      ))}
                  </div>
                </div>

                <Field
                  label="Planning SD (within-pair)"
                  hint="Used only for an approximate interval half-width, never for a power claim."
                >
                  <input
                    type="number"
                    min={0}
                    step={0.1}
                    value={design.planningSd}
                    onChange={(event) => update({ planningSd: Number(event.target.value) })}
                    disabled={Boolean(design.lockedAt)}
                    className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none focus:border-signal/40 disabled:opacity-60"
                  />
                </Field>

                <p className="rounded-lg border border-surface-border bg-white/[0.025] p-3 text-xs leading-5 text-foreground/55">
                  Planning preview:{" "}
                  {halfWidth === null
                    ? "not available — set a positive SD."
                    : `≈ ±${halfWidth.toFixed(2)} at ${design.blocks * design.blockLength} pairs.`}{" "}
                  This is a normal-approximation planning aid, not power.
                </p>
              </div>
            </Panel>
          ) : null}

          {step === 2 ? (
            <Panel className="p-5">
              <h2 className="text-base font-semibold">Design the contrast</h2>
              <p className="mt-1 text-sm leading-6 text-foreground/50">
                The allocation is previewed locally from a committed seed. It is not a randomization service.
              </p>
              <div className="mt-4 space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Condition A">
                    <input
                      value={design.conditions.a}
                      onChange={(event) => update({ conditions: { ...design.conditions, a: event.target.value } })}
                      disabled={Boolean(design.lockedAt)}
                      className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none focus:border-signal/40 disabled:opacity-60"
                    />
                  </Field>
                  <Field label="Condition B">
                    <input
                      value={design.conditions.b}
                      onChange={(event) => update({ conditions: { ...design.conditions, b: event.target.value } })}
                      disabled={Boolean(design.lockedAt)}
                      className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none focus:border-signal/40 disabled:opacity-60"
                    />
                  </Field>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  <Field label="Sessions per condition per block">
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={design.blockLength}
                      onChange={(event) => update({ blockLength: Number(event.target.value) })}
                      disabled={Boolean(design.lockedAt)}
                      className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none focus:border-signal/40 disabled:opacity-60"
                    />
                  </Field>
                  <Field label="Blocks">
                    <input
                      type="number"
                      min={1}
                      max={50}
                      value={design.blocks}
                      onChange={(event) => update({ blocks: Number(event.target.value) })}
                      disabled={Boolean(design.lockedAt)}
                      className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none focus:border-signal/40 disabled:opacity-60"
                    />
                  </Field>
                  <Field label="Washout sessions">
                    <input
                      type="number"
                      min={0}
                      max={20}
                      value={design.washout}
                      onChange={(event) => update({ washout: Number(event.target.value) })}
                      disabled={Boolean(design.lockedAt)}
                      className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none focus:border-signal/40 disabled:opacity-60"
                    />
                  </Field>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Allocation scheme">
                    <select
                      value={design.randomization}
                      onChange={(event) =>
                        update({ randomization: event.target.value as StudyDesign["randomization"] })
                      }
                      disabled={Boolean(design.lockedAt)}
                      className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-[#090b14] px-3 text-sm text-foreground/75 disabled:opacity-60"
                    >
                      <option value="block">Seeded block randomisation</option>
                      <option value="counterbalance">Counterbalanced blocks</option>
                    </select>
                  </Field>
                  <Field label="Committed seed">
                    <div className="mt-1 flex gap-2">
                      <input
                        value={design.seed}
                        onChange={(event) => update({ seed: event.target.value })}
                        disabled={Boolean(design.lockedAt)}
                        className="h-11 min-w-0 flex-1 rounded-lg border border-surface-border bg-white/[0.03] px-3 font-mono text-[12px] outline-none focus:border-signal/40 disabled:opacity-60"
                      />
                      <button
                        type="button"
                        disabled={Boolean(design.lockedAt)}
                        onClick={() => {
                          const bytes = new Uint8Array(8);
                          crypto.getRandomValues(bytes);
                          update({ seed: Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("") });
                        }}
                        className="h-11 rounded-lg border border-surface-border px-3 text-[11px] text-foreground/60 hover:bg-white/[0.04] disabled:opacity-60"
                      >
                        Generate
                      </button>
                    </div>
                  </Field>
                </div>

                <div className="rounded-lg border border-surface-border bg-white/[0.025] p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="mono-label text-foreground/40">Allocation preview</p>
                    <p className="font-mono text-[11px] text-foreground/45">
                      {totalSessions(design)} sessions · A={preview.perCondition.a} B={preview.perCondition.b} ·
                      imbalance {preview.imbalance}
                    </p>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1 font-mono text-[11px]">
                    {preview.sequence.slice(0, 72).map((condition, index) => (
                      <span
                        key={`${index}-${condition}`}
                        className={`grid h-6 w-6 place-items-center rounded border ${
                          condition === "A"
                            ? "border-signal/30 bg-signal/[0.08] text-signal"
                            : "border-lock/30 bg-lock/[0.08] text-lock"
                        }`}
                      >
                        {condition}
                      </span>
                    ))}
                    {preview.sequence.length > 72 ? (
                      <span className="grid h-6 place-items-center px-2 text-foreground/35">
                        +{preview.sequence.length - 72}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 text-[11px] leading-5 text-foreground/35">
                    Seed hash {preview.seedHash.toString(16)}. Preview only; not allocation concealment.
                  </p>
                </div>
              </div>
            </Panel>
          ) : null}

          {step === 3 ? (
            <Panel className="p-5">
              <h2 className="text-base font-semibold">Fix the analysis before data</h2>
              <p className="mt-1 text-sm leading-6 text-foreground/50">
                Changing the test, effect measure, exclusions, or stopping rule after seeing data makes the result
                exploratory. This form refuses to hide that choice.
              </p>
              <div className="mt-4 space-y-4">
                <Field label="Estimand">
                  <textarea
                    value={design.analysis.estimand}
                    onChange={(event) => updateAnalysis({ estimand: event.target.value })}
                    disabled={Boolean(design.lockedAt)}
                    rows={2}
                    className="mt-1 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 py-2 text-sm leading-6 outline-none focus:border-signal/40 disabled:opacity-60"
                  />
                </Field>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Test or summary">
                    <input
                      value={design.analysis.test}
                      onChange={(event) => updateAnalysis({ test: event.target.value })}
                      disabled={Boolean(design.lockedAt)}
                      className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none focus:border-signal/40 disabled:opacity-60"
                    />
                  </Field>
                  <Field label="Effect measure">
                    <input
                      value={design.analysis.effectMeasure}
                      onChange={(event) => updateAnalysis({ effectMeasure: event.target.value })}
                      disabled={Boolean(design.lockedAt)}
                      className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none focus:border-signal/40 disabled:opacity-60"
                    />
                  </Field>
                </div>
                <Field label="Why this effect measure?" hint="Justify it before collection, not after the largest result.">
                  <textarea
                    value={design.analysis.effectRationale}
                    onChange={(event) => updateAnalysis({ effectRationale: event.target.value })}
                    disabled={Boolean(design.lockedAt)}
                    rows={2}
                    className="mt-1 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 py-2 text-sm leading-6 outline-none focus:border-signal/40 disabled:opacity-60"
                  />
                </Field>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Expected shape">
                    <select
                      value={design.analysis.expectedShape}
                      onChange={(event) => updateAnalysis({ expectedShape: event.target.value as StudyShape })}
                      disabled={Boolean(design.lockedAt)}
                      className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-[#090b14] px-3 text-sm text-foreground/75 disabled:opacity-60"
                    >
                      {SHAPES.map((shape) => (
                        <option key={shape} value={shape}>
                          {shape}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Decision emphasis">
                    <select
                      value={design.analysis.decisionRule}
                      onChange={(event) =>
                        updateAnalysis({
                          decisionRule: event.target.value as StudyAnalysis["decisionRule"],
                        })
                      }
                      disabled={Boolean(design.lockedAt)}
                      className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-[#090b14] px-3 text-sm text-foreground/75 disabled:opacity-60"
                    >
                      <option value="support">Support</option>
                      <option value="against">Against</option>
                      <option value="inconclusive">Inconclusive</option>
                    </select>
                  </Field>
                </div>
                <Field label="What counts as support?">
                  <textarea
                    value={design.analysis.supportThreshold}
                    onChange={(event) => updateAnalysis({ supportThreshold: event.target.value })}
                    disabled={Boolean(design.lockedAt)}
                    rows={2}
                    className="mt-1 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 py-2 text-sm leading-6 outline-none focus:border-signal/40 disabled:opacity-60"
                  />
                </Field>
                <Field label="Missing data">
                  <input
                    value={design.analysis.missingData}
                    onChange={(event) => updateAnalysis({ missingData: event.target.value })}
                    disabled={Boolean(design.lockedAt)}
                    className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none focus:border-signal/40 disabled:opacity-60"
                  />
                </Field>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Exclusions">
                    <input
                      value={design.analysis.exclusions}
                      onChange={(event) => updateAnalysis({ exclusions: event.target.value })}
                      disabled={Boolean(design.lockedAt)}
                      className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none focus:border-signal/40 disabled:opacity-60"
                    />
                  </Field>
                  <Field label="Stopping rule">
                    <input
                      value={design.analysis.stoppingRule}
                      onChange={(event) => updateAnalysis({ stoppingRule: event.target.value })}
                      disabled={Boolean(design.lockedAt)}
                      className="mt-1 h-11 w-full rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none focus:border-signal/40 disabled:opacity-60"
                    />
                  </Field>
                </div>

                {validation.errors.length ? (
                  <div className="rounded-lg border border-danger/30 bg-danger/[0.055] p-3">
                    <p className="mono-label text-danger/70">Blocking</p>
                    <ul className="mt-2 space-y-1 text-xs leading-5 text-foreground/65">
                      {validation.errors.map((error) => (
                        <li key={error}>· {error}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {validation.warnings.length ? (
                  <div className="rounded-lg border border-lock/30 bg-lock/[0.055] p-3">
                    <p className="mono-label text-lock/70">Warnings, not hidden</p>
                    <ul className="mt-2 space-y-1 text-xs leading-5 text-foreground/65">
                      {validation.warnings.map((warning) => (
                        <li key={warning}>· {warning}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {!design.lockedAt ? (
                  <button
                    type="button"
                    onClick={lockPlan}
                    disabled={busy || !validation.readyToLock}
                    className="inline-flex min-h-11 w-full items-center justify-center rounded-lg border border-signal/35 bg-signal/[0.09] px-4 text-sm font-medium text-signal hover:bg-signal/[0.14] disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {busy ? "Locking…" : "Lock plan and compute hash"}
                  </button>
                ) : null}
              </div>
            </Panel>
          ) : null}

          {step === 4 ? (
            <Panel className="p-5">
              <h2 className="text-base font-semibold">Review and export</h2>
              {!design.lockedAt ? (
                <div className="mt-3 rounded-lg border border-lock/30 bg-lock/[0.05] p-4">
                  <p className="text-sm text-lock">This plan is still a draft.</p>
                  <button
                    type="button"
                    onClick={lockPlan}
                    className="mt-3 inline-flex min-h-11 items-center rounded-lg border border-signal/35 bg-signal/[0.09] px-4 text-sm text-signal"
                  >
                    Go to lock
                  </button>
                </div>
              ) : (
                <>
                  <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                    <div>
                      <dt className="mono-label text-foreground/35">Title</dt>
                      <dd className="mt-1 text-foreground/80">{design.title}</dd>
                    </div>
                    <div>
                      <dt className="mono-label text-foreground/35">Revision</dt>
                      <dd className="mt-1 font-mono text-foreground/80">{design.revision}</dd>
                    </div>
                    <div className="sm:col-span-2">
                      <dt className="mono-label text-foreground/35">SHA-256</dt>
                      <dd className="mt-1 break-all font-mono text-[11px] text-signal/75">
                        {hash ?? "not computed — Web Crypto unavailable"}
                      </dd>
                    </div>
                    <div>
                      <dt className="mono-label text-foreground/35">Primary</dt>
                      <dd className="mt-1 text-foreground/80">{primaryEvidence?.label}</dd>
                    </div>
                    <div>
                      <dt className="mono-label text-foreground/35">Sessions</dt>
                      <dd className="mt-1 font-mono text-foreground/80">{totalSessions(design)}</dd>
                    </div>
                  </dl>

                  <div className="mt-5 grid gap-2 sm:grid-cols-2">
                    <button
                      type="button"
                      onClick={() => download("md")}
                      className="inline-flex min-h-11 items-center justify-center rounded-lg border border-signal/35 bg-signal/[0.09] px-4 text-sm text-signal hover:bg-signal/[0.14]"
                    >
                      Download Markdown
                    </button>
                    <button
                      type="button"
                      onClick={() => download("json")}
                      className="inline-flex min-h-11 items-center justify-center rounded-lg border border-surface-border px-4 text-sm text-foreground/70 hover:bg-white/[0.04]"
                    >
                      Download JSON
                    </button>
                    <button
                      type="button"
                      onClick={copyMarkdown}
                      className="inline-flex min-h-11 items-center justify-center rounded-lg border border-surface-border px-4 text-sm text-foreground/70 hover:bg-white/[0.04]"
                    >
                      Copy Markdown
                    </button>
                    <button
                      type="button"
                      onClick={() => window.print()}
                      className="inline-flex min-h-11 items-center justify-center rounded-lg border border-surface-border px-4 text-sm text-foreground/70 hover:bg-white/[0.04]"
                    >
                      Print plan
                    </button>
                  </div>

                  <div className="mt-5 max-h-[420px] overflow-auto rounded-lg border border-surface-border bg-black/20 p-4">
                    <pre className="whitespace-pre-wrap font-mono text-[11px] leading-5 text-foreground/55">
                      {exported?.markdown ?? "Export will appear after locking."}
                    </pre>
                  </div>
                </>
              )}
            </Panel>
          ) : null}

          <div className="flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setStep((current) => Math.max(0, current - 1))}
              disabled={step === 0}
              className="inline-flex min-h-11 items-center rounded-lg border border-surface-border px-4 text-sm text-foreground/60 disabled:opacity-30"
            >
              Back
            </button>
            <button
              type="button"
              onClick={() => setStep((current) => Math.min(STEPS.length - 1, current + 1))}
              disabled={step === STEPS.length - 1}
              className="inline-flex min-h-11 items-center rounded-lg border border-surface-border px-4 text-sm text-foreground/60 disabled:opacity-30"
            >
              Next
            </button>
          </div>
        </div>

        <aside className="space-y-4">
          <Panel className="p-4">
            <h2 className="mono-label text-foreground/40">Plan posture</h2>
            <p className="mt-2 text-sm text-foreground/75">
              {design.lockedAt ? `Locked · revision ${design.revision}` : "Draft · not locked"}
            </p>
            <p className="mt-1 text-[11px] leading-5 text-foreground/40">
              {validation.readyToLock ? "No blocking errors." : `${validation.errors.length} blocking error(s).`}
            </p>
            <p className="mt-3 text-[11px] leading-5 text-foreground/35">
              The hash is a local integrity check. It is not a trusted timestamp or registry deposition.
            </p>
          </Panel>

          <Panel className="p-4">
            <h2 className="mono-label text-foreground/40">Claim ladder</h2>
            <ol className="mt-2 space-y-2 text-[11px] leading-5 text-foreground/45">
              <li>1. My ratings changed.</li>
              <li>2. The change is consistent with an effect in this case.</li>
              <li className="text-foreground/25">3. The practice caused improvement.</li>
              <li className="text-foreground/25">4. IMAGINA is effective.</li>
            </ol>
            <p className="mt-2 text-[11px] leading-5 text-lock/65">
              This frontend plan supports only the first two, and only after honest execution.
            </p>
          </Panel>

          <Panel className="p-4">
            <h2 className="mono-label text-foreground/40">Related</h2>
            <div className="mt-2 flex flex-col gap-1.5 text-xs">
              <Link href="/method" className="text-signal/75 underline-offset-4 hover:underline">
                Method &amp; Claim Atlas
              </Link>
              <Link href="/science" className="text-foreground/55 underline-offset-4 hover:underline">
                Scientific boundaries
              </Link>
              <Link href="/research/participant" className="text-foreground/55 underline-offset-4 hover:underline">
                Participant protocol
              </Link>
            </div>
          </Panel>
        </aside>
      </div>

      <div className="mt-8">
        <BoundaryNote>
          This is a locally generated planning artifact, not a registered report, ethics approval, or evidence of
          efficacy. It does not compute p-values, power, or treatment effects. Version {STUDY_APP_VERSION}.
        </BoundaryNote>
      </div>
    </div>
  );
}
