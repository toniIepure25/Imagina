import { describe, expect, it } from "vitest";
import { studyEligibleEvidence } from "@/lib/evidence/registry";
import {
  MODE_CEILING,
  STUDY_SCHEMA,
  createDefaultDesign,
  planningHalfWidth,
  totalSessions,
  validateStudyDesign,
  withLock,
  withNewRevision,
} from "@/lib/studyDesign";

const eligible = new Set(studyEligibleEvidence().map((entry) => entry.id));

function completeDesign() {
  const design = createDefaultDesign("2026-01-01T00:00:00.000Z");
  return {
    ...design,
    title: "Vividness under guided practice",
    question: "Does guided practice change self-reported vividness within this single case?",
  };
}

describe("study design", () => {
  it("creates a versioned default with the declared schema", () => {
    const design = createDefaultDesign();
    expect(design.schema).toBe(STUDY_SCHEMA);
    expect(design.revision).toBe(1);
    expect(design.lockedAt).toBeNull();
    expect(design.mode).toBe("personal");
  });

  it("blocks locking until the plan is specific", () => {
    const validation = validateStudyDesign(createDefaultDesign(), eligible);
    expect(validation.readyToLock).toBe(false);
    expect(validation.errors.length).toBeGreaterThan(0);

    const complete = validateStudyDesign(completeDesign(), eligible);
    expect(complete.readyToLock).toBe(true);
    expect(complete.errors).toEqual([]);
  });

  it("rejects an outcome that is not study-eligible", () => {
    const design = { ...completeDesign(), primaryOutcome: "scene.symbolic" };
    const validation = validateStudyDesign(design, eligible);
    expect(validation.readyToLock).toBe(false);
    expect(validation.errors.join(" ")).toContain("study-eligible");
  });

  it("surfaces boundaries rather than hiding them", () => {
    for (const mode of ["explore", "research"] as const) {
      const validation = validateStudyDesign({ ...completeDesign(), mode }, eligible);
      expect(validation.warnings).toContain(MODE_CEILING[mode]);
    }
    const design = completeDesign();
    expect(design.boundaries.join(" ")).toContain("Single-case");
    expect(design.boundaries.join(" ")).toContain("not a registry entry");
  });

  it("computes sessions and planning precision without claiming power", () => {
    expect(totalSessions({ blocks: 4, blockLength: 3 })).toBe(24);
    expect(totalSessions({ blocks: -1, blockLength: 3 })).toBe(0);
    expect(planningHalfWidth(1, 12)).toBeCloseTo(0.5658, 3);
    expect(planningHalfWidth(1, 0)).toBeNull();
    expect(planningHalfWidth(0, 12)).toBeNull();
  });

  it("locks and revises without mutating the source", () => {
    const design = completeDesign();
    const locked = withLock(design, "2026-02-01T00:00:00.000Z");
    expect(design.lockedAt).toBeNull();
    expect(locked.lockedAt).toBe("2026-02-01T00:00:00.000Z");
    expect(locked.revision).toBe(design.revision + 1);

    const revised = withNewRevision(locked);
    expect(revised.lockedAt).toBeNull();
    expect(revised.revision).toBe(locked.revision + 1);
  });
});
