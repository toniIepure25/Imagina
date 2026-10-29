import { describe, expect, it } from "vitest";
import type { StudioEvent } from "@/lib/animusStudioApi";
import {
  commandSummary,
  filterTraceEntries,
  mergeTraceEvents,
  normalizeTraceEvent,
  normalizeTraceEvents,
  traceTime,
} from "@/lib/tracebook";

function event(overrides: Partial<StudioEvent> & { seq: number; event_type: string }): StudioEvent {
  return {
    version_id: null,
    payload: {},
    created_at: "2026-01-02T03:04:05Z",
    ...overrides,
  } as StudioEvent;
}

describe("tracebook", () => {
  it("normalizes an intent event without inventing a version", () => {
    const entry = normalizeTraceEvent(
      event({
        seq: 4,
        event_type: "studio.intent.applied",
        version_id: "version-4",
        payload: {
          text: "make the sky violet",
          resolutions: ["set scene.atmosphere.sky.color"],
          warnings: ["Assumed a twilight palette."],
        },
      }),
    );
    expect(entry.kind).toBe("intent");
    expect(entry.title).toBe("Intent applied");
    expect(entry.intentText).toBe("make the sky violet");
    expect(entry.resolutions).toHaveLength(1);
    expect(entry.warnings).toHaveLength(1);
    expect(entry.versionId).toBe("version-4");
  });

  it("reads version ids from nested payloads", () => {
    const entry = normalizeTraceEvent(
      event({
        seq: 7,
        event_type: "studio.candidates.generated",
        payload: { source_version_id: "version-6", candidate_ids: ["a", "b"] },
      }),
    );
    expect(entry.versionId).toBe("version-6");
    expect(entry.title).toBe("Candidates generated");
    expect(entry.detail).toContain("2 candidates");
  });

  it("deduplicates by sequence and keeps the latest payload", () => {
    const first = normalizeTraceEvents([
      event({ seq: 1, event_type: "studio.undo" }),
      event({ seq: 2, event_type: "studio.redo" }),
    ]);
    const merged = mergeTraceEvents(first, [
      event({ seq: 2, event_type: "studio.branch.created", payload: { name: "Alt" } }),
      event({ seq: 3, event_type: "studio.world.saved", payload: { name: "Studio world", items: 4 } }),
    ]);
    expect(merged.map((item) => item.seq)).toEqual([1, 2, 3]);
    expect(merged[1].title).toBe("Branch created");
    expect(merged[2].detail).toContain("4 elements");
  });

  it("filters by lens and free text", () => {
    const entries = normalizeTraceEvents([
      event({ seq: 1, event_type: "studio.session.created", payload: { title: "Harbor" } }),
      event({ seq: 2, event_type: "studio.intent.applied", payload: { text: "add a lighthouse" } }),
      event({ seq: 3, event_type: "studio.candidate.selected", payload: { variant_index: 0 } }),
    ]);
    expect(filterTraceEntries(entries, "intent", "").map((item) => item.seq)).toEqual([2]);
    expect(filterTraceEntries(entries, "candidates", "").map((item) => item.seq)).toEqual([3]);
    expect(filterTraceEntries(entries, "all", "lighthouse").map((item) => item.seq)).toEqual([2]);
    expect(filterTraceEntries(entries, "all", "missing")).toHaveLength(0);
  });

  it("summarizes typed commands and tolerates malformed timestamps", () => {
    expect(commandSummary({ op: "add_entity", kind: "tree", label: "Pine" })).toBe("Add Pine");
    expect(commandSummary({ op: "remove_entity", entity_id: "e1" })).toBe("Remove e1");
    expect(commandSummary({ op: "set_scene_attribute", path: "atmosphere.fog", value: 1 })).toBe(
      "Set scene.atmosphere.fog",
    );
    expect(traceTime("not-a-date")).toBe("--:--:--");
  });
});
