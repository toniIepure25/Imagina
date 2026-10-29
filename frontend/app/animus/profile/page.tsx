"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AnimusShell from "@/components/animus/AnimusShell";
import DossierSheet from "@/components/animus/dossier/DossierSheet";
import EvidenceLedger from "@/components/animus/dossier/EvidenceLedger";
import EvidenceMark from "@/components/evidence/EvidenceMark";
import {
  getStudioProfile,
  resetStudioProfile,
  type StudioProfile,
} from "@/lib/animusStudioApi";

function Metric({
  label,
  value,
  note,
  evidenceId,
}: {
  label: string;
  value: string;
  note: string;
  evidenceId?: string;
}) {
  return (
    <div className="border-t border-rule/60 pt-2">
      <div className="flex items-center justify-between gap-2">
        <p className="dossier-label">{label}</p>
        {evidenceId ? <EvidenceMark evidenceId={evidenceId} /> : null}
      </div>
      <p className="mt-1 font-mono text-lg tabular-nums text-ink">{value}</p>
      <p className="mt-0.5 text-[11px] leading-relaxed text-ink-muted">{note}</p>
    </div>
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
    <AnimusShell active="profile">
      <div className="px-4 py-8 sm:px-6 sm:py-10">
        <DossierSheet className="p-5 sm:p-8 lg:p-10">
          <div className="flex flex-wrap items-start justify-between gap-4 border-b-2 border-ink/70 pb-5">
            <div>
              <p className="dossier-label">IMAGINA / ANIMUS · local dossier</p>
              <h1 className="dossier-display mt-2 max-w-2xl text-3xl leading-[1.05] text-ink sm:text-4xl">
                A mirror for scene practice, not a hidden-content score.
              </h1>
              <p className="mt-3 max-w-2xl text-[12px] leading-relaxed text-ink-muted">
                These estimates come from local reconstruction and recall trials on scenes you created. They
                describe task performance and confidence calibration, not hidden imagery or clinical status.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => router.push("/animus")}
                className="rounded border border-ink/25 px-3 py-1.5 text-[11px] text-ink hover:bg-ink/[0.04]"
              >
                Back to Studio
              </button>
              <button
                type="button"
                onClick={() => void reset()}
                disabled={busy || !profile}
                className="rounded border border-ink/15 px-3 py-1.5 text-[11px] text-ink-muted hover:text-ink disabled:opacity-40"
              >
                {busy ? "Resetting…" : resetArmed ? "Confirm reset" : "Reset profile"}
              </button>
            </div>
          </div>

          {error ? (
            <p role="alert" className="mt-4 border border-[#8b3a2f]/35 bg-[#8b3a2f]/[0.06] px-3 py-2 text-[11px] text-[#7c2f25]">
              {error}
            </p>
          ) : null}
          {resetArmed ? (
            <p className="mt-4 border border-[#8b6a2f]/35 bg-[#8b6a2f]/[0.06] px-3 py-2 text-[11px] leading-relaxed text-[#6e521f]">
              Confirming deletes every local practice trial and interview probe and resets all estimates. Scenes
              and worlds are not touched.
            </p>
          ) : null}

          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Evidence" value={loading ? "—" : String(profile?.trial_count ?? 0)} note="local trials recorded" />
            <Metric label="Claim level" value="L1" note="behavioural-assisted · no neural-content claim" />
            <Metric label="Privacy" value="Local" note="SQLite on this machine · no telemetry" />
            <Metric
              label="Dimensions"
              value={String(profile?.dimensions.length ?? 0)}
              note="reported separately · no composite score"
            />
          </div>

          <div className="mt-8">
            <EvidenceLedger
              dimensions={profile?.dimensions ?? []}
              trialCount={profile?.trial_count ?? 0}
              loading={loading}
            />
          </div>

          {profile?.epistemic && profile.epistemic.n_interviews > 0 ? (
            <section className="mt-8 border-t border-rule/70 pt-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="dossier-display text-xl text-ink">Epistemic interviews</h2>
                <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-muted">
                  descriptive · {profile.epistemic.n_interviews} interviews · {profile.epistemic.n_probes} probes
                </span>
              </div>
              <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
                <Metric
                  label="Mean Brier"
                  value={typeof profile.epistemic.mean_brier === "number" ? profile.epistemic.mean_brier.toFixed(3) : "—"}
                  note="lower is better"
                  evidenceId="calibration.brier"
                />
                <Metric
                  label="Overconfidence"
                  value={typeof profile.epistemic.overconfidence === "number" ? profile.epistemic.overconfidence.toFixed(3) : "—"}
                  note="mean confidence minus accuracy"
                />
                <Metric
                  label="Abstention"
                  value={typeof profile.epistemic.abstention_rate === "number" ? `${Math.round(profile.epistemic.abstention_rate * 100)}%` : "—"}
                  note="coverage, not a penalty"
                />
                <Metric
                  label="Info gain"
                  value={typeof profile.epistemic.mean_information_gain === "number" ? profile.epistemic.mean_information_gain.toFixed(3) : "—"}
                  note="realised entropy reduction"
                />
              </div>
              <p className="mt-4 text-[11px] leading-relaxed text-ink-muted">
                These summaries aggregate completed interviews only. They describe the belief-update trace, not a
                neural image, diagnosis, or composite imagination ability.
              </p>
            </section>
          ) : null}

          {profile?.contrast && profile.contrast.n_sessions > 0 ? (
            <section className="mt-8 border-t border-rule/70 pt-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="dossier-display text-xl text-ink">Scene Threshold</h2>
                <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-muted">
                  descriptive · {profile.contrast.n_completed} completed · {profile.contrast.n_trials} trials
                </span>
              </div>
              <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
                <Metric
                  label="Median threshold"
                  value={typeof profile.contrast.median_threshold === "number" ? profile.contrast.median_threshold.toFixed(3) : "—"}
                  note="within-scene units · censored estimates excluded"
                  evidenceId="threshold.dprime"
                />
                <Metric
                  label="Mean d′"
                  value={typeof profile.contrast.mean_dprime === "number" ? profile.contrast.mean_dprime.toFixed(2) : "—"}
                  note="2-AFC sensitivity"
                  evidenceId="threshold.dprime"
                />
                <Metric
                  label="Mean Brier"
                  value={typeof profile.contrast.mean_brier === "number" ? profile.contrast.mean_brier.toFixed(3) : "—"}
                  note={`${profile.contrast.calibration_n} calibration trials`}
                  evidenceId="calibration.brier"
                />
                <Metric label="Sessions" value={String(profile.contrast.n_sessions)} note="local contrast sessions" />
              </div>
              <p className="mt-4 text-[11px] leading-relaxed text-ink-muted">
                A lower threshold means finer discrimination within a scene. These values are not imagery
                strength, a diagnosis, or a fixed trait; they depend on the scene, form, and task.
              </p>
            </section>
          ) : null}

          {profile?.error_signature && profile.error_signature.n > 0 ? (
            <section className="mt-8 border-t border-rule/70 pt-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="dossier-display text-xl text-ink">Error signature</h2>
                <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-muted">
                  descriptive ·{" "}
                  {Math.max(0, profile.error_signature.n - (profile.error_signature.epistemic_n ?? 0))}{" "}
                  reconstruction trials
                  {(profile.error_signature.epistemic_n ?? 0) > 0
                    ? ` · ${profile.error_signature.epistemic_n} interview probes`
                    : ""}
                </span>
              </div>
              <div className="mt-4 grid gap-5 sm:grid-cols-3">
                <Metric label="Omissions" value={String(profile.error_signature.omissions)} note="target objects not selected" />
                <Metric label="Intrusions" value={String(profile.error_signature.intrusions)} note="decoys selected" />
                <Metric
                  label="Spatial error"
                  value={
                    typeof profile.error_signature.mean_spatial_error === "number"
                      ? profile.error_signature.mean_spatial_error.toFixed(2)
                      : "—"
                  }
                  note={`mean normalized distance · ${profile.error_signature.spatial_n} placements`}
                />
              </div>
              <p className="mt-4 text-[11px] leading-relaxed text-ink-muted">
                These counts describe how reconstruction failed, not a clinical symptom or a composite ability
                score.
              </p>
            </section>
          ) : null}

          <section className="mt-8 border-t border-rule/70 pt-5">
            <h2 className="dossier-display text-xl text-ink">Read this before interpreting a number</h2>
            <ul className="mt-3 space-y-1.5 text-[11px] leading-relaxed text-ink-muted">
              {(profile?.limitations ?? [
                "These estimates are experimental and require validation.",
                "They do not measure neural imagery, intelligence, or clinical status.",
              ]).map((limitation) => (
                <li key={limitation} className="flex gap-2">
                  <span aria-hidden="true" className="text-ink-muted">·</span>
                  <span>{limitation}</span>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-[11px] leading-relaxed text-ink-muted">
              The profile is built from practice tasks in the Studio. To add evidence, open a session and start a
              practice run. Aphantasia and hypophantasia are treated as variations, not deficits.
            </p>
          </section>

          <footer className="mt-8 flex flex-wrap items-center justify-between gap-2 border-t-2 border-ink/60 pt-3">
            <span className="dossier-label">ANIMUS · behavioural-assisted · L1</span>
            <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-ink-muted">
              local SQLite · no upload · no diagnosis
            </span>
          </footer>
        </DossierSheet>
      </div>
    </AnimusShell>
  );
}
