import { API_URL } from "@/lib/api";
import type { ImagineAsset, ImagineJob, ImagineManifest } from "./types";

const ASSET_PATH = /^\/animus\/imagine\/assets\/[A-Za-z0-9_-]{8,80}$/;

export function isAllowedAssetUrl(value: string, apiBase = API_URL): boolean {
  try {
    const base = new URL(apiBase);
    const url = value.startsWith("/") ? new URL(value, base) : new URL(value);
    return url.origin === base.origin && ASSET_PATH.test(url.pathname);
  } catch {
    return false;
  }
}

export function manifestAssetUrl(asset: ImagineAsset, apiBase = API_URL): string {
  return asset.url.startsWith("/") ? new URL(asset.url, new URL(apiBase)).toString() : asset.url;
}

function isAsset(value: unknown, apiBase: string): value is ImagineAsset {
  if (!value || typeof value !== "object") return false;
  const asset = value as Partial<ImagineAsset>;
  return (
    typeof asset.url === "string" &&
    isAllowedAssetUrl(asset.url, apiBase) &&
    typeof asset.width === "number" &&
    Number.isFinite(asset.width) &&
    asset.width > 0 &&
    asset.width <= 8192 &&
    typeof asset.height === "number" &&
    Number.isFinite(asset.height) &&
    asset.height > 0 &&
    asset.height <= 8192 &&
    typeof asset.sha256 === "string" &&
    /^[a-f0-9]{64}$/i.test(asset.sha256)
  );
}

export type ManifestResult =
  | { ok: true; manifest: ImagineManifest }
  | { ok: false; reason: string };

export function validateManifest(input: unknown, apiBase = API_URL, now = Date.now()): ManifestResult {
  if (!input || typeof input !== "object") return { ok: false, reason: "Manifest is not an object." };
  const manifest = input as Partial<ImagineManifest>;
  if (manifest.schema !== "IMAGINA-DIFFUSION-MANIFEST-v1") {
    return { ok: false, reason: "Unknown manifest schema." };
  }
  if (manifest.state !== "succeeded") return { ok: false, reason: "Manifest is not in a succeeded state." };
  if (typeof manifest.job_id !== "string" || manifest.job_id.length < 8) {
    return { ok: false, reason: "Manifest job id is invalid." };
  }
  if (!isAsset(manifest.skybox, apiBase)) return { ok: false, reason: "Skybox asset is invalid." };
  if (manifest.skybox.width > 4096 || manifest.skybox.height > 2048) {
    return { ok: false, reason: "Skybox dimensions exceed the declared maximum." };
  }
  if (!isAsset(manifest.preview, apiBase)) return { ok: false, reason: "Preview asset is invalid." };
  if (manifest.preview.width > 1280 || manifest.preview.height > 720) {
    return { ok: false, reason: "Preview dimensions exceed the declared maximum." };
  }
  if (typeof manifest.expires_at !== "string" || Number.isNaN(Date.parse(manifest.expires_at))) {
    return { ok: false, reason: "Manifest expiry is invalid." };
  }
  if (Date.parse(manifest.expires_at) <= now) return { ok: false, reason: "Manifest has expired." };
  if (typeof manifest.model_slot !== "string" || typeof manifest.model_hash !== "string") {
    return { ok: false, reason: "Manifest model provenance is missing." };
  }
  return { ok: true, manifest: manifest as ImagineManifest };
}

export function isTerminalJob(job: ImagineJob): boolean {
  return job.state === "succeeded" || job.state === "failed" || job.state === "cancelled";
}

export function jobStateLabel(state: ImagineJob["state"]): string {
  const labels: Record<ImagineJob["state"], string> = {
    queued: "Queued",
    running: "Running",
    cancelling: "Cancelling",
    cancelled: "Cancelled",
    succeeded: "Succeeded",
    failed: "Failed",
  };
  return labels[state];
}
