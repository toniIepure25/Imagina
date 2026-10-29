import { getEvidence } from "./evidence/registry";
import { buildRandomizationPreview } from "./randomization";
import {
  MODE_CEILING,
  totalSessions,
  type StudyDesign,
} from "./studyDesign";

export type ExportedPlan = {
  plan: StudyDesign;
  hash: string | null;
  markdown: string;
  json: string;
  generatedAt: string;
};

export async function hashStudyDesign(design: StudyDesign): Promise<string | null> {
  if (typeof crypto === "undefined" || !crypto.subtle) return null;
  const bytes = new TextEncoder().encode(JSON.stringify(design));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export function buildPlanExport(design: StudyDesign, hash: string | null): ExportedPlan {
  const generatedAt = new Date().toISOString();
  const plan = { ...design };
  const markdown = buildMarkdown(plan, hash);
  const json = JSON.stringify(
    {
      schema: "IMAGINA-PREREG-EXPORT-v1",
      generatedAt,
      hash,
      plan,
    },
    null,
    2,
  );
  return { plan, hash, markdown, json, generatedAt };
}

export function buildMarkdown(design: StudyDesign, hash: string | null): string {
  const primary = getEvidence(design.primaryOutcome);
  const preview = buildRandomizationPreview({
    seed: design.seed,
    blocks: design.blocks,
    blockLength: design.blockLength,
    scheme: design.randomization,
  });
  const secondary = design.secondaryOutcomes.length
    ? design.secondaryOutcomes
        .map((id) => `- ${getEvidence(id)?.label ?? id} (\`${id}\`) — secondary / exploratory`)
        .join("\n")
    : "- None declared.";
  const boundaries = design.boundaries.map((boundary) => `- ${boundary}`).join("\n");

  return `# ${design.title || "Untitled N-of-1 plan"}

**Status:** ${design.lockedAt ? "LOCAL PLAN LOCKED" : "DRAFT — NOT LOCKED"}  
**Schema:** ${design.schema} · revision ${design.revision}  
**Created:** ${design.createdAt}  
**Locked:** ${design.lockedAt ?? "not locked"}  
**Hash:** ${hash ?? "not computed — Web Crypto unavailable"}  
**Registration status:** Locally generated plan. Not a registry entry, not ethics approval, and not a Registered Report.

## Question

${design.question || "Unspecified."}

## Evidence mode and claim ceiling

- Mode: **${design.mode}**
- Ceiling: ${MODE_CEILING[design.mode]}

## Design

- Conditions: **A** = ${design.conditions.a} · **B** = ${design.conditions.b}
- Design: ${design.randomization} allocation, ${design.blocks} blocks × ${design.blockLength} sessions per condition
- Washout: ${design.washout} session(s)
- Total scheduled sessions: ${totalSessions(design)}
- Seed commitment: \`${design.seed}\`
- Allocation preview: ${preview.sequence.join(" ")}
- Preview balance: A=${preview.perCondition.a}, B=${preview.perCondition.b}

The allocation preview is not a randomization service and does not guarantee balance.

## Primary outcome

- **${primary?.label ?? design.primaryOutcome}** (\`${design.primaryOutcome}\`)
- Direction: ${design.direction}
- Minimum meaningful change: ${design.minimumMeaningfulChange}
- Source boundary: ${primary?.cannot ?? "Unregistered outcome."}

## Secondary outcomes

${secondary}

Secondary outcomes are descriptive/exploratory and do not inherit the primary decision rule.

## Analysis plan

- Estimand: ${design.analysis.estimand}
- Test / summary: ${design.analysis.test}
- Effect measure: ${design.analysis.effectMeasure}
- Rationale: ${design.analysis.effectRationale}
- Expected shape: ${design.analysis.expectedShape}
- Missing data: ${design.analysis.missingData}
- Exclusions: ${design.analysis.exclusions}
- Stopping rule: ${design.analysis.stoppingRule}
- Multiplicity: ${design.analysis.multiplicity}
- Decision rule: ${design.analysis.decisionRule}
- Support threshold: ${design.analysis.supportThreshold}

No p-values, effect estimates, or conclusions are produced by this plan. Analysis is out of scope for this frontend artifact.

## Planning precision (not power)

${
  design.planningSd > 0
    ? `Assuming independent pairs and a within-pair SD of ${design.planningSd}, the approximate 95% interval half-width is ${(
        (1.96 * design.planningSd) /
        Math.sqrt(Math.max(1, design.blocks * design.blockLength))
      ).toFixed(3)}. This is a planning approximation, not a power calculation.`
    : "Planning SD was not provided. No precision preview is available."
}

Randomization-test power depends on autocorrelation, effect size, measurement count, baseline length, carryover, and gradual effects. No single “80% power” number is shown.

## Boundaries

${boundaries}

## What this cannot show

- That the practice caused an improvement.
- That IMAGINA is effective, clinically validated, or a treatment.
- That a single case generalizes to other people.
- That self-report is an objective measure of mental imagery.
- That the allocation preview or local hash is a trusted registry deposition.

## Reporting rule

If the design was not randomized, the baseline is unstable, or the plan changed after data inspection, report a descriptive case report only — no causal or “effective” language.
`;
}

export function downloadText(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function safeFilename(title: string): string {
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
  return `imagina-prereg-${slug || "untitled"}`;
}
