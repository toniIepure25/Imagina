"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import Button from "@/components/common/Button";
import {
  getStudioProfile,
  resetStudioProfile,
  type ProfileDimension,
  type StudioProfile,
} from "@/lib/animusStudioApi";

const STATUS_LABEL: Record<string, string> = {
  no_evidence: "No evidence yet",
  collecting: "Collecting",
  provisional: "Provisional",
  moderate_evidence: "Moderate evidence",
};

function DimensionCard({ dimension }: { dimension: ProfileDimension }) {
  const value = dimension.estimate;
  const brier = typeof dimension.brier_score === "number" ? dimension.brier_score : null;
  const isCalibration = dimension.id === "calibration" && brier !== null;
  const percent = value === null ? 0 : Math.round(value * 100);
  const display =
    dimension.id === "calibration" && brier !== null
      ? brier.toFixed(2)
      : value === null
        ? "—"
        : `${percent}%`;
  const barPercent =
    dimension.id === "calibration" && brier !== null
      ? Math.max(0, Math.min(100, Math.round((1 - brier) * 100)))
      : percent;
  return (
    <article className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-medium text-foreground/90">{dimension.label}</h2>
          <p className="mt-1 text-xs leading-relaxed text-foreground/45">{dimension.description}</p>
        </div>
        <span className="shrink-0 rounded-full border border-white/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-foreground/45">
          {STATUS_LABEL[dimension.status] ?? dimension.status}
        </span>
      </div>
      <div className="mt-5 flex items-end justify-between">
        <span className="text-3xl font-semibold tabular-nums tracking-tight">
          {display}
          {isCalibration ? <span className="ml-1 text-xs font-normal text-foreground/35">Brier</span> : null}
        </span>
        <span className="text-[11px] text-foreground/35">
          {dimension.n} trial{dimension.n === 1 ? "" : "s"}
          {dimension.n > 0 ? ` · ±${Math.round(dimension.uncertainty * 100)} pts` : ""}
        </span>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10" aria-hidden="true">
        <div
          className="h-full rounded-full bg-gradient-to-r from-accent-glow/80 to-accent/80"
          style={{ width: `${barPercent}%` }}
        />
      </div>
      <p className="mt-3 text-[11px] text-foreground/35">
        {dimension.id === "calibration" && brier !== null
          ? `Brier score ${brier.toFixed(3)} · lower means confidence tracks correctness.`
          : dimension.n < 3
            ? "At least three trials are required before an estimate is shown."
            : "Experimental behavioural estimate; not a diagnosis."}
      </p>
    </article>
  );
}

export default function AnimusProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<StudioProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [resetArmed, setResetArmed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void getStudioProfile()
      .then((result) => {
        if (active) setProfile(result);
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : String(caught));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const reset = async () => {
    if (busy) return;
    if (!resetArmed) {
      setResetArmed(true);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setProfile(await resetStudioProfile());
      setResetArmed(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-6xl px-6 py-12">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <span className="inline-flex rounded-full border border-accent-glow/25 bg-accent-glow/[0.06] px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-accent-glow/75">
              ANIMUS · behavioural profile
            </span>
            <h1 className="mt-4 max-w-2xl text-3xl font-semibold tracking-tight md:text-4xl">
              A mirror for scene practice, not a hidden-content score.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-foreground/50">
              These estimates come from local reconstruction and recall trials on scenes you created. They
              describe task performance and confidence calibration, not hidden imagery or clinical status.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={() => router.push("/animus")}>
              Back to Studio
            </Button>
            <Button variant="ghost" onClick={reset} disabled={busy || !profile}>
              {busy ? "Resetting…" : resetArmed ? "Confirm reset" : "Reset profile"}
            </Button>
          </div>
        </div>

        {error ? (
          <p className="mt-6 rounded-xl border border-red-400/20 bg-red-400/[0.06] px-4 py-3 text-sm text-red-200/80">
            {error}
          </p>
        ) : null}
        {resetArmed ? (
          <p className="mt-6 rounded-xl border border-amber-300/20 bg-amber-300/[0.04] px-4 py-3 text-xs text-amber-100/70">
            Confirming deletes every local practice trial and interview probe and resets all estimates.
            Scenes and worlds are not touched.
          </p>
        ) : null}

        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
            <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">Evidence</p>
            <p className="mt-2 text-3xl font-semibold tabular-nums">
              {loading ? "—" : profile?.trial_count ?? 0}
            </p>
            <p className="mt-1 text-xs text-foreground/40">local trials recorded</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
            <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">Claim level</p>
            <p className="mt-2 text-lg font-medium">L1 · behavioural</p>
            <p className="mt-1 text-xs text-foreground/40">No neural-content claim</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
            <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">Privacy</p>
            <p className="mt-2 text-lg font-medium">Local only</p>
            <p className="mt-1 text-xs text-foreground/40">No uploads, no telemetry</p>
          </div>
        </div>

        <section className="mt-10">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium">Dimensions</h2>
            <span className="text-[11px] text-foreground/35">No composite score by design.</span>
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {loading ? (
              <p className="text-sm text-foreground/40">Loading local profile…</p>
            ) : (
              (profile?.dimensions ?? []).map((dimension) => (
                <DimensionCard key={dimension.id} dimension={dimension} />
              ))
            )}
          </div>
        </section>

        {profile?.epistemic && profile.epistemic.n_interviews > 0 ? (
          <section className="mt-10 rounded-2xl border border-white/10 bg-white/[0.025] p-6">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-sm font-medium">Epistemic interviews</h2>
              <span className="text-[11px] text-foreground/35">
                descriptive · {profile.epistemic.n_interviews} interviews · {profile.epistemic.n_probes} probes
              </span>
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">Mean Brier</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {typeof profile.epistemic.mean_brier === "number"
                    ? profile.epistemic.mean_brier.toFixed(3)
                    : "—"}
                </p>
                <p className="mt-1 text-[11px] text-foreground/40">lower is better</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">Overconfidence</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {typeof profile.epistemic.overconfidence === "number"
                    ? profile.epistemic.overconfidence.toFixed(3)
                    : "—"}
                </p>
                <p className="mt-1 text-[11px] text-foreground/40">mean confidence minus accuracy</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">Abstention</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {typeof profile.epistemic.abstention_rate === "number"
                    ? `${Math.round(profile.epistemic.abstention_rate * 100)}%`
                    : "—"}
                </p>
                <p className="mt-1 text-[11px] text-foreground/40">coverage, not a penalty</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">Info gain</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {typeof profile.epistemic.mean_information_gain === "number"
                    ? profile.epistemic.mean_information_gain.toFixed(3)
                    : "—"}
                </p>
                <p className="mt-1 text-[11px] text-foreground/40">mean realised entropy reduction</p>
              </div>
            </div>
            <p className="mt-4 text-[11px] leading-relaxed text-foreground/35">
              These summaries aggregate completed interviews only. They describe the belief-update trace,
              not a neural image, diagnosis, or composite imagination ability.
            </p>
          </section>
        ) : null}

        {profile?.contrast && profile.contrast.n_sessions > 0 ? (
          <section className="mt-10 rounded-2xl border border-white/10 bg-white/[0.025] p-6">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-sm font-medium">Scene Threshold</h2>
              <span className="text-[11px] text-foreground/35">
                descriptive · {profile.contrast.n_completed} completed · {profile.contrast.n_trials} trials
              </span>
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">Median threshold</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {typeof profile.contrast.median_threshold === "number"
                    ? profile.contrast.median_threshold.toFixed(3)
                    : "—"}
                </p>
                <p className="mt-1 text-[11px] text-foreground/40">
                  within-scene units; censored estimates excluded
                </p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">Mean d′</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {typeof profile.contrast.mean_dprime === "number"
                    ? profile.contrast.mean_dprime.toFixed(2)
                    : "—"}
                </p>
                <p className="mt-1 text-[11px] text-foreground/40">2-AFC sensitivity</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">Mean Brier</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {typeof profile.contrast.mean_brier === "number"
                    ? profile.contrast.mean_brier.toFixed(3)
                    : "—"}
                </p>
                <p className="mt-1 text-[11px] text-foreground/40">
                  {profile.contrast.calibration_n} calibration trials
                </p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">Sessions</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">{profile.contrast.n_sessions}</p>
                <p className="mt-1 text-[11px] text-foreground/40">local contrast sessions</p>
              </div>
            </div>
            <p className="mt-4 text-[11px] leading-relaxed text-foreground/35">
              A lower threshold means finer discrimination within a scene. These values are not imagery
              strength, a diagnosis, or a fixed trait; they depend on the scene, form, and task.
            </p>
          </section>
        ) : null}

        {profile?.error_signature && profile.error_signature.n > 0 ? (
          <section className="mt-10 rounded-2xl border border-white/10 bg-white/[0.025] p-6">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-sm font-medium">Error signature</h2>
              <span className="text-[11px] text-foreground/35">
                descriptive ·{" "}
                {Math.max(0, profile.error_signature.n - (profile.error_signature.epistemic_n ?? 0))}{" "}
                reconstruction trials
                {(profile.error_signature.epistemic_n ?? 0) > 0
                  ? ` · ${profile.error_signature.epistemic_n} interview probes`
                  : ""}
              </span>
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              <div>
                <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">Omissions</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">{profile.error_signature.omissions}</p>
                <p className="mt-1 text-[11px] text-foreground/40">target objects not selected</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">Intrusions</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">{profile.error_signature.intrusions}</p>
                <p className="mt-1 text-[11px] text-foreground/40">decoys selected</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">Spatial error</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">
                  {typeof profile.error_signature.mean_spatial_error === "number"
                    ? profile.error_signature.mean_spatial_error.toFixed(2)
                    : "—"}
                </p>
                <p className="mt-1 text-[11px] text-foreground/40">
                  mean normalized distance · {profile.error_signature.spatial_n} placements
                </p>
              </div>
            </div>
            <p className="mt-4 text-[11px] leading-relaxed text-foreground/35">
              These counts describe how reconstruction failed, not a clinical symptom or a composite ability
              score.
            </p>
          </section>
        ) : null}

        <section className="mt-10 rounded-2xl border border-white/10 bg-white/[0.025] p-6">
          <h2 className="text-sm font-medium">Read this before interpreting a number</h2>
          <ul className="mt-3 space-y-2 text-xs leading-relaxed text-foreground/45">
            {(profile?.limitations ?? [
              "These estimates are experimental and require validation.",
              "They do not measure neural imagery, intelligence, or clinical status.",
            ]).map((limitation) => (
              <li key={limitation} className="flex gap-2">
                <span className="text-accent-glow/60">·</span>
                <span>{limitation}</span>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-foreground/40">
            The profile is built from practice tasks in the Studio. To add evidence, open a session and
            start a practice run. Aphantasia and hypophantasia are treated as variations, not deficits.
          </p>
        </section>
      </div>
    </AppShell>
  );
}
