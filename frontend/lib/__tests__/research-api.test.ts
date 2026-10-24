import { describe, it, expect } from "vitest";

describe("research-api types", () => {
  it("should have Study interface fields", async () => {
    const { getStudyMode, listStudies, listInstruments } = await import("../research-api");
    expect(typeof getStudyMode).toBe("function");
    expect(typeof listStudies).toBe("function");
    expect(typeof listInstruments).toBe("function");
  });
});

describe("api module", () => {
  it("should export apiFetch", async () => {
    const { apiFetch } = await import("../api");
    expect(typeof apiFetch).toBe("function");
  });
});
