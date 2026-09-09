# C3XD — Temporal Contract (raw BIDS event timing, ds005191 v1.0.2)

Certified from `*_events.tsv` (all 6 subjects, testImagery + testPerception). TR = **1.0 s** (72 slices,
slice-timing present). No BOLD inspected. Full manifest: `results/c3xd/c3xd_event_timing_manifest.json`.

## Imagery trial structure (per trial, verified)
`trial_type` codes: **-2 = preparation cue** (verbal description; `cueID`), **2 = imagery** (eyes-closed
recall; `imageryID`), **3 = post-imagery target video** (`stimID`), **-5 = evaluation**
(accuracy+vividness); -1/-3/-4/-6/-7 = fixation/rest/gaps. Each trial's cue, imagery and video share the
**same video identity**.

Order and separation (S1 representative; consistent across subjects):
- **cue → imagery gap = 0 s** (imagery block begins exactly at cue offset — the collinearity risk).
- **imagery → video gap = 2 s** (target video begins 2 s after imagery offset).
- **cue duration is strongly JITTERED: {4,5,6,7,8,9,10,11,12,13,14,17} s** (subject reads a
  variable-length description, then indicates readiness).
- **imagery duration varies: {12,13,14,17,18,23} s**; **video duration varies: {10,11,12,15,16,21} s**.

## Why the design is potentially identifiable despite the 0 s cue→imagery gap
Although the imagery block abuts the cue, both the **cue and imagery durations vary trial-to-trial**
(4–17 s cue, 12–23 s imagery). Convolving these variable-length boxcars with a canonical HRF yields
cue and imagery regressors whose shapes and areas differ per trial, so the two are **not perfectly
collinear** and a GLM/LSS can in principle estimate separate cue and imagery amplitudes. The video is
additionally offset by imagery-duration + 2 s (≈14–25 s after imagery onset), well within HRF-separable
range. **Whether this in-principle separability is sufficient in practice is decided empirically by the
frozen synthetic injected-signal recovery** (`c3xd_design_simulation.json`), not asserted here.

## Contract certification (all 6 subjects)
- Imagery: **360 trials = 72 videos × 5 sessions**, exactly **5 reps/video**, each session contains all
  72 videos once (session balance ✓) — matches the C3XC/frozen contract; independent unit = session.
- Perception: **72 videos** presented (5 reps/video).
- 72/72 imagery↔perception video-identity correspondence (video ids shared across tasks).

## Storage / feasibility note (see raw_acquisition_plan.json)
Raw testImagery+testPerception BOLD = **139.4 GB** (trainPerception excluded), peak ≈ 223 GB with
preprocessing intermediates, vs **37.1 GB** free → **storage insufficient** for the raw BOLD extraction
in this environment (a sealed fail-closed condition). The event-timing audit and the synthetic
identifiability analysis (which need only events.tsv) are unaffected and are executed in full.
