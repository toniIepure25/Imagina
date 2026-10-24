# Scientific Limitations (Phase 2)

What IMAGINA's multimodal platform has and has not shown. Verdicts use predeclared criteria
(`backend/app/multimodal/validation/*`, `results/phase2/SUMMARY.json`). Post-hoc additions are labelled as such.

## 1. Nothing here shows that IMAGINA improves imagery

- No participant has used the closed loop. All closed-loop results are simulations with a scripted synthetic responder.
- Protocols E–G exist only as preregistration drafts (`docs/research/MM_PREREG_E_F_G.md`) and design simulations.
- Self-report remains the only direct measure of vividness (see §3).

## 2. Validation is component-level and mostly single-dataset

- Each pipeline was checked on one public dataset (ECG: MIT-BIH; respiration: BIDMC; EDA: Non-EEG; fNIRS: MNE motor;
  MEG: MNE sample; EEG: ds005815; fusion: eegmat). Populations (ICU patients, arrhythmia patients, healthy students)
  differ from future imagery-training participants.
- fNIRS and MEG validations use **one participant each**; they test processing correctness, not population effects.
- Several comparisons are against reference *implementations* (MNE, MNE-NIRS, NeuroKit2, pyriemann), not ground truth.
  Where our code delegates to MNE (fNIRS OD/mBLL), agreement tests integration, not independent physics.

## 3. Mental imagery specifically

- The only local dataset with imagery and trial-level vividness is ds005815 (YOTO). Its vividness ratings are
  ceiling-skewed (58% are 5/5).
- Perception-vs-imagery phase decoding is confounded by visual input and time-in-trial; it does not show decoding of
  imagery content. Imagery *content* decoding (face vs square) is evaluated separately.
- No fMRI imagery data were used in this phase. NOD is closed for development (project rule) and the NSD imagery work
  lives in earlier gates (C3/C3M: imagery transfer NULL). No claim of imagery decoding from fMRI is made.
- No paired EEG–fMRI–MEG recordings exist in the project; none were fabricated or simulated as paired.

## 4. Known method issues (open)

- **EDA:** SCR detection disagrees with NeuroKit2 (F1 0.38; 0.50 with matched relative thresholds, post hoc) — the
  response definition differs and there is no event-level ground truth to adjudicate. The EDA-only artifact detector
  did not respond to treadmill motion (accelerometry confirms motion); motion-artifact handling is unvalidated.
  The Non-EEG EDA unit is undocumented (header "NU"); absolute thresholds assume µS. Tonic agreement (r ≈ 1) is
  uninformative because both tools split at 0.05 Hz.
- **EDA onset timing:** improved on synthetic data from −0.31 s to −0.09…−0.19 s bias; real-data onset accuracy cannot
  be validated without annotated onsets.
- **MEG bad channels:** the first run pooled magnetometers and gradiometers (29 channels flagged); fixed (per-type scoring,
  minimum 4× variance ratio). The two bad-channel criteria were added post hoc.
- **Latency:** stage timings were measured on a shared pod whose cgroup quota (16 CPUs) is far below the 256 visible
  cores; thread oversubscription produced ~100 ms throttling quanta in tails. Sensor-to-host and render latency were
  not measured (no hardware marker loop).
- **Synchronization:** constant transport latency is unobservable from host receive timestamps (BrainFlow, ADS1299 over
  host time); such streams report unknown alignment uncertainty and the controller holds adaptation by default.

## 5. Requirements before supervised human neurofeedback studies

1. Ethics approval for a specific protocol; consent covering biosignal storage and retention.
2. Completion of the hardware safety checklist for any device (independent electrical safety review); commercial,
   certified amplifiers preferred over DIY hardware.
3. Measured end-to-end latency with a hardware marker loop.
4. Pilot (no efficacy analysis) to estimate variance for the E/F sample size.
5. A validated, individually calibrated predictor for any physiological dimension that the controller adapts to — or
   explicit acceptance that the adaptive arm adapts to self-report and experimental proxies only.
