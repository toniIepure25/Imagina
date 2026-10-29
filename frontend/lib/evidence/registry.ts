import raw from "./registry.json";
import type { EvidenceEntry, EvidenceRegistry } from "./types";

const registry = raw as EvidenceRegistry;
const byId = new Map(registry.entries.map((entry) => [entry.id, entry]));

export const EVIDENCE_REGISTRY = registry;
export const EVIDENCE_ENTRIES = registry.entries;

export function getEvidence(id: string | null | undefined): EvidenceEntry | null {
  if (!id) return null;
  return byId.get(id) ?? null;
}

export function isKnownEvidence(id: string | null | undefined): boolean {
  return Boolean(getEvidence(id));
}

export function evidenceForSurface(pathname: string | null | undefined): EvidenceEntry[] {
  if (!pathname) return [];
  return registry.entries.filter((entry) => entry.surfaces.some((surface) => matchesSurface(surface, pathname)));
}

export function matchesSurface(surface: string, pathname: string): boolean {
  if (surface === pathname) return true;
  if (surface === "/") return pathname === "/";
  const surfaceParts = surface.split("/").filter(Boolean);
  const pathParts = pathname.split("/").filter(Boolean);
  if (surfaceParts.length !== pathParts.length) return false;
  return surfaceParts.every((part, index) => part.startsWith("[") || part === pathParts[index]);
}

export function evidenceCounts(): Record<string, number> {
  return registry.entries.reduce<Record<string, number>>((counts, entry) => {
    counts[entry.kind] = (counts[entry.kind] ?? 0) + 1;
    return counts;
  }, {});
}

export function studyEligibleEvidence(): EvidenceEntry[] {
  return registry.entries.filter((entry) => entry.studyEligible);
}
