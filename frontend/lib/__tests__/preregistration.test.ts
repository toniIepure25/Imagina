import { describe, expect, it } from "vitest";
import { studyEligibleEvidence } from "@/lib/evidence/registry";
import { buildMarkdown, buildPlanExport, hashStudyDesign, safeFilename } from "@/lib/preregistration";
import { createDefaultDesign, type StudyDesign } from "@/lib/studyDesign";

function completeDesign(): StudyDesign {
  const design = createDefaultDesign("2026-01-01T00:00:00.000Z");
  return {
    ...design,
    title: "Vividness under guided practice",
    question: "Does guided practice change self-reported vividness within this single case?",
    secondaryOutcomes: [studyEligibleEvidence().find((entry) => entry.id !== design.primaryOutcome)!.id],
  };
}

describe("pre-registration export", () => {
  it("hashes the same design reproducibly", async () => {
    const design = completeDesign();
    const first = await hashStudyDesign(design);
    const second = await hashStudyDesign(design);
    expect(first).toBe(second);
    if (first) expect(first).toMatch(/^[0-9a-f]{64}$/);
  });

  it("exports a versioned JSON envelope", () => {
    const exported = buildPlanExport(completeDesign(), "abc123");
    const parsed = JSON.parse(exported.json);
    expect(parsed.schema).toBe("IMAGINA-PREREG-EXPORT-v1");
    expect(parsed.hash).toBe("abc123");
    expect(parsed.plan.title).toBe("Vividness under guided practice");
    expect(exported.markdown).toContain("IMAGINA-PREREG-v1");
  });

  it("states precision and registration boundaries in the plan", () => {
    const markdown = buildMarkdown(completeDesign(), "deadbeef");
    expect(markdown).toContain("Planning precision (not power)");
    expect(markdown).toContain("not a power calculation");
    expect(markdown).toContain("not a registry entry");
    expect(markdown).toContain("not ethics approval");
    expect(markdown).toContain("No p-values");
    expect(markdown).toContain("DRAFT — NOT LOCKED");
  });

  it("shows a locked status only after lock", () => {
    const design = { ...completeDesign(), lockedAt: "2026-02-01T00:00:00.000Z" };
    expect(buildMarkdown(design, null)).toContain("LOCAL PLAN LOCKED");
  });

  it("creates stable, safe filenames", () => {
    expect(safeFilename("Vividness under guided practice")).toBe("imagina-prereg-vividness-under-guided-practice");
    expect(safeFilename("  ***  ")).toBe("imagina-prereg-untitled");
    expect(safeFilename("A".repeat(80)).length).toBeLessThanOrEqual(63);
  });
});
