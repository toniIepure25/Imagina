import type { WorkbenchView } from "@/lib/workbenchState";

export interface WorkbenchLink {
  view: WorkbenchView | null;
  versionId: string | null;
  candidateId: string | null;
}

const VIEWS: WorkbenchView[] = ["stage", "structure", "ledger", "trace"];

function cleanId(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > 200) return null;
  if (!/^[A-Za-z0-9._:-]+$/.test(trimmed)) return null;
  return trimmed;
}

function cleanView(value: string | null): WorkbenchView | null {
  return VIEWS.includes(value as WorkbenchView) ? (value as WorkbenchView) : null;
}

export function parseWorkbenchQuery(search: string): WorkbenchLink {
  const params = new URLSearchParams(search);
  const versionId = cleanId(params.get("version"));
  return {
    view: cleanView(params.get("view")),
    versionId,
    candidateId: versionId ? null : cleanId(params.get("candidate")),
  };
}

export function buildWorkbenchQuery(link: WorkbenchLink): string {
  const params = new URLSearchParams();
  if (link.versionId) params.set("version", link.versionId);
  else if (link.candidateId) params.set("candidate", link.candidateId);
  if (link.view && link.view !== "stage") params.set("view", link.view);
  const query = params.toString();
  return query ? `?${query}` : "";
}
