import { describe, it, expect } from "vitest";

describe("EEG Validation page", () => {
  it("exports default component", async () => {
    const mod = await import("../../../app/research/eeg-validation/page");
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe("function");
  });
});
