import { describe, it, expect } from "vitest";

describe("OperatorDashboard", () => {
  it("exports default component", async () => {
    const mod = await import("../OperatorDashboard");
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe("function");
  });
});

describe("SafeguardStatus derivation", () => {
  it("should not contain hardcoded green checkmarks", async () => {
    const mod = await import("../OperatorDashboard");
    const source = mod.default.toString();
    expect(source).not.toContain("&#10003;");
  });
});
