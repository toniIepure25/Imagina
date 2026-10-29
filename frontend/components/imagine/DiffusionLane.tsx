"use client";

import { assetUrl } from "@/lib/imagine/client";
import { isTerminalJob, jobStateLabel } from "@/lib/imagine/manifest";
import type { ImagineCapabilities, ImagineJob } from "@/lib/imagine/types";

export default function DiffusionLane({
  capabilities,
  job,
  busy,
  error,
  usingSkybox,
  onRequest,
  onCancel,
  onToggleSkybox,
  onDownload,
}: {
  capabilities: ImagineCapabilities | null;
  job: ImagineJob | null;
  busy: boolean;
  error: string | null;
  usingSkybox: boolean;
  onRequest: () => void;
  onCancel: () => void;
  onToggleSkybox: () => void;
  onDownload: () => void;
}) {
  const diffusion = capabilities?.diffusion;
  const blocked = !diffusion || diffusion.status === "blocked";
  const preview = job?.manifest ? assetUrl(job, "preview") : null;
  const terminal = job ? isTerminalJob(job) : false;

  return (
    <div className="space-y-3" data-testid="diffusion-lane">
      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
        <div className="flex items-center justify-between gap-2">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-foreground/35">Diffusion lane</p>
          <span
            className={`rounded-full border px-2 py-0.5 font-mono text-[11px] uppercase tracking-[0.12em] ${
              blocked ? "border-lock/30 text-lock/80" : "border-signal/30 text-signal"
            }`}
          >
            {blocked ? "offline" : "ready"}
          </span>
        </div>
        <p className="mt-2 text-[11px] leading-5 text-foreground/40">
          {diffusion?.reason ?? "Remote diffusion is disabled by local configuration."}
        </p>
        <p className="mt-1 font-mono text-[11px] text-foreground/30">
          {diffusion?.model_slot ?? "scene-diffusion-v0"} · skybox {diffusion?.max_skybox.width ?? 4096}×
          {diffusion?.max_skybox.height ?? 2048}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onRequest}
            disabled={blocked || busy || Boolean(job && !terminal)}
            className="inline-flex min-h-11 items-center rounded-lg border border-signal/30 bg-signal/[0.06] px-3 font-mono text-[11px] uppercase tracking-[0.1em] text-signal disabled:cursor-not-allowed disabled:opacity-40"
          >
            {job && !terminal ? "Request in flight" : "Request skybox"}
          </button>
          <button
            type="button"
            onClick={onDownload}
            className="inline-flex min-h-11 items-center rounded-lg border border-white/10 px-3 font-mono text-[11px] uppercase tracking-[0.1em] text-foreground/55 hover:border-white/25"
          >
            Download request
          </button>
        </div>
      </div>

      {error ? (
        <p role="alert" className="rounded-lg border border-lock/25 bg-lock/[0.06] px-3 py-2 text-[11px] leading-5 text-lock/80">
          {error}
        </p>
      ) : null}

      {job ? (
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3" aria-live="polite">
          <div className="flex items-center justify-between gap-2">
            <span className="font-mono text-[11px] text-foreground/60">{job.id}</span>
            <span
              className={`font-mono text-[11px] uppercase tracking-[0.12em] ${
                job.state === "failed" ? "text-lock" : job.state === "succeeded" ? "text-signal" : "text-[#e8b45a]"
              }`}
            >
              {jobStateLabel(job.state)}
            </span>
          </div>
          {job.staged ? <p className="mt-1 font-mono text-[11px] text-foreground/35">stage: {job.staged}</p> : null}
          {job.error_message ? <p className="mt-1 text-[11px] text-lock/70">{job.error_message}</p> : null}
          {preview ? (
            <div
              role="img"
              aria-label="Generated environment preview"
              className="mt-2 aspect-video w-full rounded-lg border border-white/10 bg-cover bg-center"
              style={{ backgroundImage: `url(${preview})` }}
            />
          ) : null}
          {job.state === "succeeded" && job.manifest ? (
            <div className="mt-2 space-y-2">
              <p className="font-mono text-[11px] text-foreground/35">
                model {job.manifest.model_hash.slice(0, 12)} · seed {job.manifest.seed} · expires{" "}
                {new Date(job.manifest.expires_at).toLocaleTimeString()}
              </p>
              <button
                type="button"
                onClick={onToggleSkybox}
                className="inline-flex min-h-11 w-full items-center justify-center rounded-lg border border-signal/30 bg-signal/[0.08] px-3 font-mono text-[11px] uppercase tracking-[0.1em] text-signal"
              >
                {usingSkybox ? "Return to procedural sky" : "Use diffusion skybox"}
              </button>
            </div>
          ) : null}
          {!terminal ? (
            <button
              type="button"
              onClick={onCancel}
              disabled={busy}
              className="mt-2 inline-flex min-h-11 w-full items-center justify-center rounded-lg border border-white/10 px-3 font-mono text-[11px] uppercase tracking-[0.1em] text-foreground/50 disabled:opacity-40"
            >
              Cancel job
            </button>
          ) : null}
        </div>
      ) : null}

      <p className="text-[11px] leading-5 text-foreground/30">
        Generated skybox is an environment texture, not a reconstruction. Geometry, collision, and first-person
        navigation stay local and symbolic.
      </p>
    </div>
  );
}
