import { describe, it, expect } from "vitest";

describe("multimodalApi", () => {
  it("exports session and control functions", async () => {
    const mod = await import("../multimodalApi");
    for (const fn of [mod.createSession, mod.stepSession, mod.sendCommand, mod.getSync, mod.getDecisions,
      mod.getCorridor, mod.verifyReplay, mod.runProtocol, mod.getHardwareChecklist]) {
      expect(typeof fn).toBe("function");
    }
  });

  it("labels every evidence class and source kind", async () => {
    const { EVIDENCE_LABELS, SOURCE_LABELS, isSimulated } = await import("../multimodalApi");
    expect(EVIDENCE_LABELS.EXPERIMENTAL_PROXY).toBe("Experimental proxy");
    expect(SOURCE_LABELS.REAL_SENSOR).toBe("REAL SENSOR");
    expect(isSimulated(["SYNTHETIC", "REPLAY"])).toBe(true);
    expect(isSimulated(["SYNTHETIC", "REAL_SENSOR"])).toBe(false);
    expect(isSimulated([])).toBe(false);
  });
});
