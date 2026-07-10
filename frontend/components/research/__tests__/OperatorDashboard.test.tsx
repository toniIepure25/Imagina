import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

describe("OperatorDashboard", () => {
  it("exports default component", async () => {
    const mod = await import("../OperatorDashboard");
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe("function");
  });
});

describe("SafeguardStatus derivation", () => {
  const src = readFileSync(
    resolve(__dirname, "../OperatorDashboard.tsx"),
    "utf-8"
  );

  it("should not contain hardcoded green checkmarks", () => {
    expect(src).not.toContain("&#10003;");
  });

  it('should not have unconditional verified status for policy items', () => {
    const lines = src.split("\n");
    const policyItems = ["Local data only", "Pseudonym-only identification"];
    for (const item of policyItems) {
      const idx = lines.findIndex((l) => l.includes(item));
      expect(idx).toBeGreaterThan(-1);
      const context = lines.slice(Math.max(0, idx - 2), idx + 3).join("\n");
      expect(context).toContain("policy_only");
      expect(context).not.toMatch(/status:\s*"verified"/);
    }
  });
});
