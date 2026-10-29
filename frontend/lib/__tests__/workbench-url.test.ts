import { describe, expect, it } from "vitest";
import { buildWorkbenchQuery, parseWorkbenchQuery } from "../workbenchUrl";

describe("workbench URL links", () => {
  it("round-trips a version preview", () => {
    const query = buildWorkbenchQuery({ view: "ledger", versionId: "version-2", candidateId: null });
    expect(query).toBe("?version=version-2&view=ledger");
    expect(parseWorkbenchQuery(query)).toEqual({
      view: "ledger",
      versionId: "version-2",
      candidateId: null,
    });
  });

  it("round-trips a candidate preview and omits the default stage", () => {
    const query = buildWorkbenchQuery({ view: "stage", versionId: null, candidateId: "candidate-1" });
    expect(query).toBe("?candidate=candidate-1");
    expect(parseWorkbenchQuery(query)).toEqual({
      view: null,
      versionId: null,
      candidateId: "candidate-1",
    });
  });

  it("ignores malformed identifiers and unknown views", () => {
    expect(parseWorkbenchQuery("?version=../../etc&view=canvas&candidate=ok-1")).toEqual({
      view: null,
      versionId: null,
      candidateId: "ok-1",
    });
  });

  it("prefers a version when both ids are present", () => {
    expect(parseWorkbenchQuery("?version=v1&candidate=c1")).toEqual({
      view: null,
      versionId: "v1",
      candidateId: null,
    });
  });

  it("returns an empty string for no link", () => {
    expect(buildWorkbenchQuery({ view: "stage", versionId: null, candidateId: null })).toBe("");
  });
});
