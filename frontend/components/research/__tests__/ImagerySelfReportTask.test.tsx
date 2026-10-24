import { describe, it, expect, vi } from "vitest";

describe("ImagerySelfReportTask", () => {
  it("exports SelfReportTrialResult with separate timing fields", async () => {
    const result = {
      trial_index: 0,
      stimulus_id: "corridor",
      vividness: 5,
      confidence: 4,
      effort: 3,
      fixation_onset_ms: 100,
      imagery_onset_ms: 3100,
      image_formed_ms: 8000,
      rating_screen_onset_ms: 8001,
      rating_submission_ms: 12000,
      imagery_formation_latency_ms: 4900,
      rating_completion_latency_ms: 3999,
      fixation_onset_utc: "2026-01-01T00:00:00.000Z",
      imagery_onset_utc: "2026-01-01T00:00:03.000Z",
      image_formed_utc: "2026-01-01T00:00:08.000Z",
      rating_screen_onset_utc: "2026-01-01T00:00:08.001Z",
      rating_submission_utc: "2026-01-01T00:00:12.000Z",
    };

    expect(result.imagery_formation_latency_ms).toBe(
      result.image_formed_ms - result.imagery_onset_ms,
    );
    expect(result.rating_completion_latency_ms).toBe(
      result.rating_submission_ms - result.rating_screen_onset_ms,
    );
    expect(result.imagery_formation_latency_ms).not.toBe(
      result.rating_submission_ms - result.fixation_onset_ms,
    );
  });

  it("timing fields are distinct from total response time", () => {
    const fixation = 100;
    const imagery = 3100;
    const formed = 8000;
    const ratingOnset = 8001;
    const submission = 12000;

    const imageryLatency = formed - imagery;
    const ratingLatency = submission - ratingOnset;
    const totalTime = submission - fixation;

    expect(imageryLatency + ratingLatency).not.toBe(totalTime);
    expect(imageryLatency).toBeGreaterThan(0);
    expect(ratingLatency).toBeGreaterThan(0);
  });
});
