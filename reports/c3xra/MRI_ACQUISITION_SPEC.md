# C3XRA — MRI Acquisition Specification (design-only)

**Gate:** C3XRA Independent Acquisition Readiness. **Status:** prospective specification. **No human data
has been or will be acquired in this gate.** All numeric parameters are frozen in
`results/c3xra/mri_sequence_contract.json` (self-hashed) and must be **confirmed and phantom-tested at the
specific 3T facility** before participant 001. Vendor protocol *names* are not fabricated; only generic,
verifiable sequence families are named.

## 1. Scanner & coil
- **3.0 T** MRI scanner.
- **≥ 32-channel** head coil, whole-brain BOLD coverage.

## 2. Functional (BOLD) — frozen targets
| Parameter | Value |
|---|---|
| Sequence | 2D multiband gradient-echo EPI |
| Voxel | 2.0 × 2.0 × 2.0 mm (≤ 2 mm isotropic) |
| TR | 1.5 s |
| TE | 30 ms |
| Flip angle | 65° |
| Multiband factor | 4 |
| Slices | 60, transverse, whole brain |
| Phase-encode | AP |
| FOV / matrix | 208 × 208 mm / 104 × 104 |
| Partial Fourier | none |
| Dummy scans discarded | 4 |

## 3. Distortion correction
- **Spin-echo EPI AP/PA fieldmap pair**, geometry matched to the BOLD, for susceptibility distortion
  correction in fMRIPrep. A short **PA blip** (3 volumes) is also acquired.

## 4. Anatomical
- **T1w MPRAGE**, 1.0 mm isotropic, whole head, for surface reconstruction and normalization.

## 5. Synchronization
- Scanner emits a **TTL pulse per volume**; the PsychoPy task waits for the **first TTL** and timestamps it,
  so every event onset is expressed relative to acquisition start. Trigger desync tolerance is sealed in
  `results/c3xra/acquisition_qc_seal.json`.

## 6. Preprocessing target
- **fMRIPrep → MNI152NLin2009cAsym, 2 mm, NO spatial smoothing** (pinned in
  `results/c3xra/preprocessing_execution_seal.json`).

## 7. Vendor notes (to confirm on-site — not protocol names)
- **Siemens:** multiband via CMRR or product MB-EPI; AP/PA fieldmap.
- **Philips:** MB-SENSE EPI; dynamic stabilization off.
- **GE:** HyperBand EPI; confirm slice/MB support with the physicist.

## 8. Confirmation required before acquisition
Exact sequence card, multiband availability, and timing **must be confirmed and phantom-tested** at the
named facility. This document does not authorize scanning; see `C3XRA_READINESS_DECISION.json` for external
prerequisites.
