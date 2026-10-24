# ANIMUS Observatory — evidence, contrast, and stability

**Status:** experimental, local-only, code complete but unexecuted on the current host.
**Claim level:** `L1_BEHAVIORAL_ASSISTED`. The observatory is a descriptive view of behavioural
evidence. It is not a neural image, a diagnosis, a causal explanation of memory, or a composite ability
score.

## Purpose

The Studio already contains three different kinds of evidence:

1. **Belief evidence** from the epistemic reconstruction interview (`eri-v1`): binary probes, Beta
   posteriors, entropy, coverage, and calibration.
2. **Discrimination evidence** from Scene Threshold (`contrast-v1` / `sdt-v1`): 2-AFC sensitivity,
   within-scene thresholds, side bias, and confidence calibration.
3. **Longitudinal evidence** from repeated contrast sessions on the same scene: aligned feature
   thresholds, a test–retest correlation, measurement error, and a minimal detectable change.

The observatory puts those layers side by side without collapsing them into one number. It is a
*provenance-aware memory observatory*: every belief row shows where its evidence came from, and every
result shows what it does not establish.

## Route

`/animus/observatory/[sessionId]` — opened from the Studio (“Observatory”) or directly.

The observatory anchors on the latest completed contrast session, or on the latest completed interview
when no contrast exists. Interview evidence is attached only when the interview's `scene_hash` matches the
anchor, so the atlas and the contrast result describe the same scene.

The page runs a Scene Threshold session, then shows the confidence atlas, evidence trail, and reliability
panel. The belief layer is populated when the session has a completed epistemic interview; otherwise it
stays empty and says so.

## API

`GET /animus/studio/sessions/{session_id}/observatory`

The response contains:

| Field | Meaning |
|---|---|
| `source_version_id` | Scene version used for the belief layer |
| `scene_hash` | Content hash used to align repeated contrast sessions |
| `belief` | ERI reconstruction: objects, relations, entropy, scores |
| `evidence` | Per-variable provenance, posterior, uncertainty, leave-one-out delta, sources |
| `discrimination` | Latest completed contrast result for this session, or an unavailable marker |
| `reliability` | Test–retest status, r, CI, SEM, MDC95, occasions, d′ change |
| `boundaries` | Fixed claim-boundary strings |
| `claim_level` | Always `L1_BEHAVIORAL_ASSISTED` |

## Evidence provenance

Provenance is assigned per variable, not per person:

| Value | Meaning |
|---|---|
| `direct_probe` | At least one answered probe targeted this variable |
| `prior` | No probe targeted it; the posterior remains at the prior |
| `abstained` | Only abstentions targeted it; the posterior did not move |
| `mixed` | Both answered and abstained probes targeted it |

`leave_one_out_delta` is the largest absolute change in the variable's posterior when one answered source
is removed and the remaining records are replayed. It is a sensitivity diagnostic, not a causal effect.
`dependence_group` marks probes that share an object or a relation pair, so repeated evidence is not
mistaken for independent evidence. Sources deliberately omit correctness: the observatory is not a
feedback screen, and exposing per-probe correctness would turn the interview into a learning task.

## Confidence atlas

The atlas is a top-down sketch, not a rendered mental image:

- Position comes from the symbolic scene's normalized x/z coordinates.
- Colour encodes provenance.
- Opacity encodes the posterior mean.
- Radius encodes uncertainty (`1 - |2p - 1|`).
- Relation evidence is drawn as a line between the two entities.
- Decoy variables without a scene entity are placed in a residual row.
- A table repeats every value for screen readers and for exact inspection.

The atlas does not claim that the person "sees" this layout. It is a compact view of a stated belief
model over a symbolic scene.

## Reliability

The unit of analysis is the **feature**, not the person. With one person and two occasions, a person-level
intraclass correlation is not identifiable, so the observatory does not report one.

Two completed contrast sessions on the same `scene_hash` are aligned by feature key. Censored thresholds are
excluded from alignment because a boundary value is not an identified estimate. When at least three
features have a non-censored threshold on both occasions:

```text
r = Pearson correlation across aligned feature thresholds
r_ci = Fisher-z 95% interval
SEM = sd(difference scores) / sqrt(2)
MDC95 = 1.96 × sqrt(2) × SEM
```

Otherwise the status is `insufficient` and only the occasion table and descriptive change are shown.
With the current two continuous feature types (`spatial_position`, `object_color`), a real session will
usually be `insufficient`; this is intentional rather than a hidden failure. Adding more feature types or
more occasions is a prerequisite for a stable correlation.

`dprime_change` is the latest `follow_up` minus the `baseline` occasion; if no explicit follow-up exists,
the last and first completed occasions are used. A change smaller than `MDC95` is not distinguishable from
measurement error in this sample. The reliability panel does not label a change as improvement,
training, or transfer.

## Boundaries

The observatory does not:

- decode neural content, dreams, or hidden visual experience;
- generate or reconstruct an image;
- diagnose aphantasia or any clinical condition;
- produce a composite "imagination score" or percentile;
- claim that practice generalises beyond the measured task;
- treat abstention as a failure or low confidence as a deficit;
- compare thresholds across scenes, displays, or people.

Aphantasia and hypophantasia are treated as variations and as design constraints. The product must remain
usable when visual imagery is weak or absent; strategy reflection and non-visual routes are explicit.

## Related documents

- [Scene Threshold spec](CONTRAST_SPEC.md)
- [Epistemic interview spec](EPISTEMIC_INTERVIEW_SPEC.md)
- [Measurement model](MEASUREMENT_MODEL.md)
- [Evidence map](EVIDENCE_MAP.md)
- [Claims boundary](ANIMUS_CLAIMS_BOUNDARY.md)
- [Validation protocol](VALIDATION_PROTOCOL.md)
