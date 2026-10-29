import { API_URL } from "@/lib/api";
import { manifestAssetUrl } from "./manifest";
import type { ImagineCapabilities, ImagineDiffusionRequest, ImagineJob, ImagineJobList } from "./types";

export class ImagineApiError extends Error {
  code: string;
  status: number;
  retryable: boolean;

  constructor(code: string, message: string, status: number, retryable = false) {
    super(message);
    this.name = "ImagineApiError";
    this.code = code;
    this.status = status;
    this.retryable = retryable;
  }
}

async function readError(response: Response): Promise<ImagineApiError> {
  try {
    const body = (await response.json()) as { code?: string; message?: string; retryable?: boolean };
    return new ImagineApiError(
      body.code ?? "request_failed",
      body.message ?? `Request failed (${response.status}).`,
      response.status,
      Boolean(body.retryable),
    );
  } catch {
    return new ImagineApiError("request_failed", `Request failed (${response.status}).`, response.status);
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) throw await readError(response);
  return (await response.json()) as T;
}

export function getCapabilities(): Promise<ImagineCapabilities> {
  return requestJson<ImagineCapabilities>("/animus/imagine/capabilities");
}

export function createJob(payload: ImagineDiffusionRequest): Promise<ImagineJob> {
  return requestJson<ImagineJob>("/animus/imagine/jobs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getJob(jobId: string): Promise<ImagineJob> {
  return requestJson<ImagineJob>(`/animus/imagine/jobs/${encodeURIComponent(jobId)}`);
}

export function cancelJob(jobId: string): Promise<ImagineJob> {
  return requestJson<ImagineJob>(`/animus/imagine/jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: "POST",
    body: "{}",
  });
}

export async function listJobs(limit = 5): Promise<ImagineJob[]> {
  const result = await requestJson<ImagineJobList>(`/animus/imagine/jobs?limit=${limit}`);
  return result.jobs;
}

export function assetUrl(job: ImagineJob, kind: "skybox" | "preview"): string | null {
  const asset = job.manifest?.[kind];
  return asset ? manifestAssetUrl(asset) : null;
}

export function downloadJobRequest(payload: ImagineDiffusionRequest): void {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "imagina-diffusion-request-v2.json";
  anchor.click();
  URL.revokeObjectURL(url);
}
