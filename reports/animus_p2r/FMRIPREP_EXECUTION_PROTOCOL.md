# ANIMUS-P2-R — fMRIPrep Execution Protocol (frozen)

The single pinned preprocessing pipeline for the entire confirmatory cohort. Frozen before any real run;
resource flags may differ per subject only if scientifically neutral. No scientific flag varies by subject.

## Environment (pinned)
- Container: `nipreps/fmriprep@sha256:9aec0b83b3728795fa5a593d373c9bc5d4a7034e943a793173408e3b70e702c6`
  (same digest used for the C3XAT cohort on this cluster). FreeSurfer, ANTs, AFNI, TemplateFlow bundled.
- Template: **MNI152NLin2009cAsym**, resolution **res-2** (2 mm) — the exact grid of the sealed Wang25 MPM.
  No MNI152NLin6, no fsaverage, no subject-local atlas, no functional-localizer substitution.

## Inputs
- Raw BIDS root: NOD `ds004496` v2.1.2 (staged on the PVC under `/work/animus_p2r/raw/`).
- Eligible subjects (frozen denominator): sub-01 … sub-06 (ImageNet multi-session; raw T1w + ~40 imagenet
  BOLD runs + events + fieldmaps verified). BOLD: TR 2 s, TE 0.034 s, PE `j-`, SliceTiming present.

## Command (per subject; only resource flags may differ)
```
fmriprep /work/animus_p2r/raw /work/animus_p2r/derivatives/fmriprep participant \
  --participant-label <SUB> \
  --output-spaces MNI152NLin2009cAsym:res-2 \
  --fs-license-file /work/<fs-license>.txt \
  --nthreads <N> --omp-nthreads <O> --mem-mb <M> \
  --bids-filter-file /work/animus_p2r/imagenet_filter.json \
  --skip-bids-validation false --notrack --stop-on-first-crash \
  --work-dir /work/animus_p2r/work/<SUB>
```
- `imagenet_filter.json` restricts functional processing to `task-imagenet` runs (the perception content);
  the anatomical workflow and fieldmaps are unaffected. This is an operational scope choice, not a
  scientific change (identities/estimand unchanged for the imagenet perception task).
- **No spatial smoothing** (fMRIPrep does not smooth; none added downstream).
- **Fieldmaps:** use the dataset-provided BIDS fieldmaps (present for all eligible subjects); single
  predeclared behavior; no per-subject variation and no post-hoc choice by visual/decoding quality.
- Slice-timing: fMRIPrep default (SliceTiming present in sidecars).
- CIFTI: disabled.

## Required outputs (technical QC, no decoding)
Per subject/run: `*_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold.nii.gz` + boldref + brain mask +
`*_desc-confounds_timeseries.tsv`, and the anat `*_from-T1w_to-MNI152NLin2009cAsym_*` / inverse transforms.
Certify grid/affine/orientation against the sealed Wang25 target; finite coverage; confounds present.

## Reproducibility
For ≥1 subject, a clean re-run must reproduce grid/affine/ROI membership/transform provenance (bit-identity
where feasible; otherwise a prospectively justified numeric tolerance for the BOLD). Recorded in
`results/animus_p2r/spatial/`.

## Firewall
No decoding metric (M/2AFC/retrieval/decoder CV) is computed during download/fMRIPrep/QC/feature bundling.
Decoder smoke tests use synthetic data only. Confirmatory metrics run only after
`P2R_CONFIRMATORY_IMPLEMENTATION_FREEZE.json` is committed + CI-green.
