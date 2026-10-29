export const STUDY_SCHEMA = "IMAGINA-PREREG-v1";
export const STUDY_APP_VERSION = "4.0.0";

export type StudyMode = "explore" | "personal" | "research";
export type StudyDirection = "increase" | "decrease";
export type StudyShape = "immediate" | "gradual" | "delayed" | "temporary";

export type StudyAnalysis = {
  estimand: string;
  test: string;
  effectMeasure: string;
  effectRationale: string;
  missingData: string;
  exclusions: string;
  stoppingRule: string;
  decisionRule: "support" | "against" | "inconclusive";
  supportThreshold: string;
  multiplicity: string;
  expectedShape: StudyShape;
};

export type StudyDesign = {
  schema: typeof STUDY_SCHEMA;
  appVersion: string;
  mode: StudyMode;
  title: string;
  question: string;
  primaryOutcome: string;
  direction: StudyDirection;
  minimumMeaningfulChange: number;
  secondaryOutcomes: string[];
  conditions: { a: string; b: string };
  blockLength: number;
  blocks: number;
  washout: number;
  randomization: "block" | "counterbalance";
  seed: string;
  planningSd: number;
  analysis: StudyAnalysis;
  boundaries: string[];
  createdAt: string;
  lockedAt: string | null;
  revision: number;
};

export const MODE_CEILING: Record<StudyMode, string> = {
  explore: "Hypothesis-generating only. No confirmatory p-values or efficacy language.",
  personal:
    "Descriptive case report, or a randomization test only when the plan was fixed before data and the data are complete.",
  research: "External protocol review and ethics approval are required before any collection.",
};

export function createDefaultDesign(createdAt = new Date().toISOString()): StudyDesign {
  return {
    schema: STUDY_SCHEMA,
    appVersion: STUDY_APP_VERSION,
    mode: "personal",
    title: "",
    question: "",
    primaryOutcome: "selfreport.vividness",
    direction: "increase",
    minimumMeaningfulChange: 1,
    secondaryOutcomes: [],
    conditions: { a: "Guided imagery practice", b: "Rest / control" },
    blockLength: 3,
    blocks: 4,
    washout: 1,
    randomization: "block",
    seed: "IMAGINA-LOCAL",
    planningSd: 1,
    analysis: {
      estimand: "Difference in mean self-reported vividness between conditions within this case.",
      test: "Randomization test over the pre-specified allocation.",
      effectMeasure: "Mean paired difference (A − B).",
      effectRationale: "Chosen before collection because it maps to the primary rating scale.",
      missingData: "Report missing trials; do not impute the primary analysis.",
      exclusions: "No post-hoc exclusions. Any deviation is reported.",
      stoppingRule: "Complete all pre-specified blocks; no optional stopping.",
      decisionRule: "inconclusive",
      supportThreshold: "A pre-specified minimum change plus an interval that excludes no change.",
      multiplicity: "One primary outcome and one contrast; secondary outcomes are descriptive.",
      expectedShape: "immediate",
    },
    boundaries: [
      "Single-case findings do not establish population efficacy or clinical benefit.",
      "Self-report is reactive and expectancy-prone.",
      "This plan is not a registry entry, ethics approval, or a Registered Report.",
    ],
    createdAt,
    lockedAt: null,
    revision: 1,
  };
}

export function totalSessions(design: Pick<StudyDesign, "blocks" | "blockLength">): number {
  return Math.max(0, design.blocks) * Math.max(0, design.blockLength) * 2;
}

export function planningHalfWidth(sdDiff: number, pairs: number): number | null {
  if (!Number.isFinite(sdDiff) || !Number.isFinite(pairs) || sdDiff <= 0 || pairs <= 0) return null;
  return (1.96 * sdDiff) / Math.sqrt(pairs);
}

export type StudyValidation = {
  errors: string[];
  warnings: string[];
  readyToLock: boolean;
};

export function validateStudyDesign(design: StudyDesign, eligibleOutcomeIds: Set<string>): StudyValidation {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (design.title.trim().length < 5) errors.push("Give the plan a specific title (at least 5 characters).");
  if (design.question.trim().length < 20) errors.push("State the question in at least 20 characters.");
  if (!eligibleOutcomeIds.has(design.primaryOutcome)) {
    errors.push("Choose one study-eligible primary outcome from the registry.");
  }
  if (!Number.isFinite(design.minimumMeaningfulChange) || design.minimumMeaningfulChange <= 0) {
    errors.push("State a minimum meaningful change greater than zero.");
  }
  if (design.secondaryOutcomes.includes(design.primaryOutcome)) {
    errors.push("The primary outcome cannot also be a secondary outcome.");
  }
  if (!Number.isFinite(design.blockLength) || design.blockLength < 1) errors.push("Block length must be at least 1.");
  if (!Number.isFinite(design.blocks) || design.blocks < 1) errors.push("Use at least one block.");
  if (!Number.isFinite(design.washout) || design.washout < 0) errors.push("Washout cannot be negative.");
  if (design.seed.trim().length < 3) errors.push("Commit a seed of at least 3 characters.");
  if (!design.conditions.a.trim() || !design.conditions.b.trim()) errors.push("Name both conditions.");
  if (!design.analysis.estimand.trim()) errors.push("State the estimand.");
  if (!design.analysis.test.trim()) errors.push("State the test or summary.");
  if (!design.analysis.effectMeasure.trim()) errors.push("State the effect measure.");
  if (!design.analysis.effectRationale.trim()) errors.push("Justify the effect measure before collection.");
  if (!design.analysis.missingData.trim()) errors.push("State the missing-data rule.");
  if (!design.analysis.stoppingRule.trim()) errors.push("State the stopping rule.");
  if (!design.analysis.supportThreshold.trim()) errors.push("State what would count as support.");

  if (design.blocks < 4) warnings.push("Fewer than four blocks gives a short, unstable baseline.");
  if (design.washout === 0) warnings.push("No washout: carryover between conditions is plausible.");
  if (design.mode === "explore") warnings.push(MODE_CEILING.explore);
  if (design.mode === "research") warnings.push(MODE_CEILING.research);
  if (design.secondaryOutcomes.length > 4) {
    warnings.push("More than four secondary outcomes increases multiplicity and reporting burden.");
  }
  if (design.analysis.expectedShape !== "immediate") {
    warnings.push(
      `The expected shape is “${design.analysis.expectedShape}”. Confirm that the test and summary target that shape, not an immediate step.`,
    );
  }
  if (!Number.isFinite(design.planningSd) || design.planningSd <= 0) {
    warnings.push("Planning SD is not set; precision cannot be previewed.");
  }

  return { errors, warnings, readyToLock: errors.length === 0 };
}

export function withLock(design: StudyDesign, lockedAt = new Date().toISOString()): StudyDesign {
  return { ...design, lockedAt, revision: design.revision + 1 };
}

export function withNewRevision(design: StudyDesign): StudyDesign {
  return { ...design, lockedAt: null, revision: design.revision + 1 };
}
