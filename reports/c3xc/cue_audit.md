# C3XC — Cue / Contamination Audit (Mind Captioning imagery)

**Verdict: `CUE_CONTROLLED`** (for the reliability-qualification question), assessed over the
reliable (imagery-PASS) subjects. No upgrade of an ambiguous verdict was performed.

## Paradigm and the specific risks
Each test-imagery trial is **cued recall of a previously-memorized dynamic video**; the subject
re-generates the remembered content internally and rates accuracy and vividness. Risks the audit must
address: (1) the recall cue's own content, (2) leakage from a later presentation of the target video,
(3) HRF spillover / previous trial, (4) block-averaging / temporal preprocessing.

## A. Temporal window
The released preprocessed imagery sample is a **single block-averaged amplitude per recall trial**
(braindat is 148513 voxels × 360 samples = 72 videos × 5 sessions; one vector per recall), built from
the recall period after hemodynamic-delay shift (Horikawa/KamitaniLab pipeline). There is **no
within-trial time axis** in the release, so a within-trial early-vs-late split is **not computable**
here; it would require raw BIDS ds005191 + a GLM and is recorded as a deferred limitation (it does not
gate C3XC).

## B. Target-presentation leakage — structurally ABSENT
In the imagery samples `stimID = 0` and `cueID = 0` (verified): **no target video is presented during
the recall trial**. The later/other presentation of the video lives in the separate testPerception
runs, not in the imagery samples. Therefore target-video pixel/motion leakage into the imagery-period
estimate is **structurally impossible** under this release — the strongest form of the leakage concern
is eliminated by construction, not merely argued away.

## C. ROI-profile control (HVC vs early visual V1)
A visual/word cue artifact would be **early-visual (V1) dominated**; genuine internally-generated
(recalled) content is expected to be **higher-visual-cortex (HVC: LOC/FFA/PPA/EBA/…) dominated**.
Per-subject imagery reliability by ROI (point R_I):

| Subject | VC R_I | V1 R_I | LVC R_I | HVC R_I | HVC>V1 | imagery gate |
|---|---|---|---|---|---|---|
| S1 | 0.172 | 0.121 | 0.111 | 0.204 | yes | PASS |
| S2 | 0.114 | 0.029 | 0.043 | 0.147 | yes | PASS |
| S3 | 0.200 | 0.154 | 0.145 | 0.224 | yes | PASS |
| S4 | 0.047 | 0.054 | 0.059 | 0.043 | no  | MARGINAL (near noise) |
| S5 | 0.074 | 0.043 | 0.043 | 0.094 | yes | PASS |
| S6 | 0.081 | 0.012 | 0.031 | 0.105 | yes | PASS |

**HVC > V1 for every imagery-PASS subject (5/5).** The reliable imagery signal is higher-visual-cortex
dominant, i.e. consistent with recalled semantic/event content and **against** a V1-dominated cue
artifact. The single exception (S4) is a MARGINAL, near-noise-floor subject whose ROI profile is
uninformative about contamination of the *reliable* signal, so it does not overturn the verdict. (V1
does carry some reliability in recall — expected for vivid visual imagery — but it does not dominate.)

## Verdict and scope
`CUE_CONTROLLED`: target-presentation leakage is structurally absent, and the reliable imagery is
HVC-dominant rather than V1/cue-dominant. This is scoped to the **reliability qualification**; it does
not certify a full within-trial cue-vs-recall dissociation (deferred, needs raw BIDS). Per the sealed
rule, CUE_CONTROLLED permits the primary reliability to stand; no ambiguous verdict was upgraded.
