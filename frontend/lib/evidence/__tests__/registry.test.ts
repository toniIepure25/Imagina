import { describe, expect, it } from "vitest";
import audit from "../audit.json";
import {
  EVIDENCE_ENTRIES,
  EVIDENCE_REGISTRY,
  evidenceCounts,
  evidenceForSurface,
  getEvidence,
  isKnownEvidence,
  matchesSurface,
  studyEligibleEvidence,
} from "../registry";

describe("evidence registry", () => {
  it("publishes a versioned schema and unique identifiers", () => {
    expect(EVIDENCE_REGISTRY.schema).toBe("IMAGINA-EVIDENCE-REGISTRY-v1");
    const ids = EVIDENCE_ENTRIES.map((entry) => entry.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids.length).toBeGreaterThanOrEqual(12);
  });

  it("gives every entry a complete falsifiability record", () => {
    for (const entry of EVIDENCE_ENTRIES) {
      expect(entry.label.length).toBeGreaterThan(2);
      expect(entry.what.length).toBeGreaterThan(10);
      expect(entry.method.length).toBeGreaterThan(10);
      expect(entry.source.length).toBeGreaterThan(3);
      expect(entry.uncertainty.length).toBeGreaterThan(5);
      expect(entry.cannot.length).toBeGreaterThan(5);
      expect(entry.surfaces.length).toBeGreaterThan(0);
      expect(["measured", "derived", "simulated", "narrative"]).toContain(entry.kind);
    }
  });

  it("resolves known and unknown identifiers without throwing", () => {
    expect(getEvidence("iqi.proxy")?.id).toBe("iqi.proxy");
    expect(isKnownEvidence("iqi.proxy")).toBe(true);
    expect(getEvidence("missing.metric")).toBeNull();
    expect(isKnownEvidence(null)).toBe(false);
  });

  it("matches concrete and dynamic surfaces", () => {
    expect(matchesSurface("/reports/[sessionId]", "/reports/abc")).toBe(true);
    expect(matchesSurface("/reports/[sessionId]", "/reports/abc/extra")).toBe(false);
    expect(matchesSurface("/", "/")).toBe(true);
    expect(matchesSurface("/", "/science")).toBe(false);
    expect(evidenceForSurface("/science").some((entry) => entry.id === "iqi.proxy")).toBe(true);
    expect(evidenceForSurface("/animus/imagine").some((entry) => entry.id === "imagine.scene")).toBe(true);
  });

  it("counts kinds and exposes study-eligible outcomes", () => {
    const counts = evidenceCounts();
    expect(Object.values(counts).reduce((total, count) => total + count, 0)).toBe(EVIDENCE_ENTRIES.length);
    expect(studyEligibleEvidence().length).toBeGreaterThan(0);
    expect(studyEligibleEvidence().every((entry) => entry.studyEligible)).toBe(true);
  });

  it("keeps the generated audit consistent with the registry", () => {
    expect(audit.schema).toBe("IMAGINA-EVIDENCE-AUDIT-v1");
    expect(audit.status).toBe("pass");
    expect(audit.orphanIds).toEqual([]);
    expect(audit.evidenceIdCount).toBeGreaterThanOrEqual(10);
    expect(audit.evidenceIdCount).toBe(audit.evidenceIds.length);
    for (const id of audit.evidenceIds) expect(isKnownEvidence(id)).toBe(true);
    for (const finding of audit.findings) expect(finding.negated).toBe(true);
  });
});
