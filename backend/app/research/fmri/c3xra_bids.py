"""C3XRA BIDS mock-dataset generator (design-only; SYNTHETIC data, NO human/neural data).

Emits a minimal, spec-conformant BIDS dataset for a single SYNTHETIC participant so the acquisition/BIDS
contract can be validated (official bids-validator in CI; structural self-check locally). NIfTI volumes are
tiny deterministic noise — they carry NO brain, NO signal, NO identity, NO outcome. Task events are read
from the frozen deterministic schedule so onsets are reproducible.
"""
from __future__ import annotations

import json
import os

import nibabel as nib
import numpy as np

from app.research.fmri import c3xra_schedule as S
from app.research.fmri import c3xra_task as T

MOCK_SUBJECT = "9001"          # synthetic id, clearly outside any real range
TR = 1.5
BOLD_SHAPE = (8, 8, 6)          # tiny; validity only, not analysis
AFFINE = np.diag([2.0, 2.0, 2.0, 1.0])


def _save_bold(path: str, n_vols: int, seed: int):
    rng = np.random.default_rng(S.MASTER_SEED ^ 0xB1D5 ^ seed)
    data = rng.standard_normal((*BOLD_SHAPE, n_vols)).astype(np.float32)
    img = nib.Nifti1Image(data, AFFINE)
    img.header.set_zooms((2.0, 2.0, 2.0, TR))
    img.header.set_xyzt_units("mm", "sec")
    nib.save(img, path)


def _save_anat(path: str):
    rng = np.random.default_rng(S.MASTER_SEED ^ 0xA4A7)
    img = nib.Nifti1Image(rng.standard_normal((10, 10, 8)).astype(np.float32), np.diag([1.0, 1.0, 1.0, 1.0]))
    nib.save(img, path)


def _write_json(path: str, obj: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def _imagery_events(participant_index: int, unit: int, run: int) -> list[dict]:
    """Deterministic events.tsv rows (onset/duration/trial_type/identity) from the frozen task timing."""
    from app.research.fmri.c3xra_task import (
        CUE_S,
        EVAL_S,
        GAP_CUE_IMAGERY,
        GAP_IMAGERY_POST,
        GAP_POST_EVAL,
        IMAGERY_S,
        ITI,
        LEAD_IN_S,
        POSTVIDEO_S,
        _jitter_seq,
    )
    rows = [r for r in S.imagery_trials(participant_index, max(unit, 1))
            if r["imagery_unit"] == unit and r["run"] == run]
    rows.sort(key=lambda r: r["run_position"])
    n = len(rows)
    gci = _jitter_seq(participant_index * 100 + unit * 10 + run + 1, n, *GAP_CUE_IMAGERY)
    gip = _jitter_seq(participant_index * 100 + unit * 10 + run + 2, n, *GAP_IMAGERY_POST)
    gpe = _jitter_seq(participant_index * 100 + unit * 10 + run + 3, n, *GAP_POST_EVAL)
    iti = _jitter_seq(participant_index * 100 + unit * 10 + run + 4, n, *ITI)
    out = []
    t = LEAD_IN_S
    for i, r in enumerate(rows):
        vid = r["video_id"]
        out.append({"onset": round(t, 3), "duration": CUE_S, "trial_type": "cue", "identity": vid})
        t += CUE_S + gci[i]
        out.append({"onset": round(t, 3), "duration": IMAGERY_S, "trial_type": "imagery", "identity": vid})
        t += IMAGERY_S + gip[i]
        out.append({"onset": round(t, 3), "duration": POSTVIDEO_S, "trial_type": "postvideo", "identity": vid})
        t += POSTVIDEO_S + gpe[i]
        out.append({"onset": round(t, 3), "duration": EVAL_S, "trial_type": "eval", "identity": "n/a"})
        t += EVAL_S + iti[i]
    return out, t


def _write_events(path: str, rows: list[dict]):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("onset\tduration\ttrial_type\tidentity\n")
        for r in rows:
            f.write(f"{r['onset']}\t{r['duration']}\t{r['trial_type']}\t{r['identity']}\n")


def _bold_json(task: str) -> dict:
    return {"RepetitionTime": TR, "EchoTime": 0.030, "FlipAngle": 65, "TaskName": task,
            "PhaseEncodingDirection": "j-", "SliceTiming": [0.0] * BOLD_SHAPE[2],
            "MultibandAccelerationFactor": 4}


def generate(root: str, imagery_units: int = 2, imagery_runs: int = 1,
             perception_units: int = 1) -> dict:
    """Write a minimal spec-conformant mock dataset under `root`. Returns a manifest of files written.
    (imagery_units/runs kept small: BIDS validity does not depend on trial count.)"""
    p = 1
    sub = f"sub-{MOCK_SUBJECT}"
    os.makedirs(root, exist_ok=True)
    _write_json(os.path.join(root, "dataset_description.json"),
                {"Name": "C3XRA synthetic mock (design-only; no human data)", "BIDSVersion": "1.9.0",
                 "DatasetType": "raw", "Authors": ["C3XRA design gate"]})
    with open(os.path.join(root, "participants.tsv"), "w", encoding="utf-8") as f:
        f.write("participant_id\tspecies\n" + f"{sub}\tsynthetic\n")
    with open(os.path.join(root, "README"), "w", encoding="utf-8") as f:
        f.write("SYNTHETIC mock BIDS dataset for C3XRA acquisition-readiness validation. No human data.\n")
    with open(os.path.join(root, ".bidsignore"), "w", encoding="utf-8") as f:
        f.write("")
    _write_json(os.path.join(root, "task-imagery_bold.json"), _bold_json("imagery"))
    _write_json(os.path.join(root, "task-perception_bold.json"), _bold_json("perception"))

    files = []
    for ses in range(1, imagery_units + 1):
        base = os.path.join(root, sub, f"ses-{ses:02d}")
        for sub_dir in ("func", "anat", "fmap"):
            os.makedirs(os.path.join(base, sub_dir), exist_ok=True)
        # anat once per session (T1w)
        anat = os.path.join(base, "anat", f"{sub}_ses-{ses:02d}_T1w.nii.gz")
        _save_anat(anat)
        files.append(anat)
        # fieldmap AP/PA
        for d, lbl in (("AP", "j-"), ("PA", "j")):
            fm = os.path.join(base, "fmap", f"{sub}_ses-{ses:02d}_dir-{d}_epi.nii.gz")
            _save_bold(fm, 3, seed=ses * 10 + (0 if d == "AP" else 1))
            files.append(fm)
            _write_json(fm.replace(".nii.gz", ".json"),
                        {"PhaseEncodingDirection": lbl, "TotalReadoutTime": 0.05, "TaskName": "n/a",
                         "IntendedFor": []})
        # imagery func runs
        for run in range(1, imagery_runs + 1):
            ev, dur = _imagery_events(p, ses, run)
            n_vols = int(np.ceil((dur + T.TAIL_S) / TR))
            stem = f"{sub}_ses-{ses:02d}_task-imagery_run-{run:02d}"
            bold = os.path.join(base, "func", f"{stem}_bold.nii.gz")
            _save_bold(bold, n_vols, seed=ses * 100 + run)
            files.append(bold)
            _write_events(os.path.join(base, "func", f"{stem}_events.tsv"), ev)
    # perception unit (run-pair) in its own session block after imagery
    for u in range(1, perception_units + 1):
        ses = imagery_units + u
        base = os.path.join(root, sub, f"ses-{ses:02d}")
        os.makedirs(os.path.join(base, "func"), exist_ok=True)
        for which in ("A", "B"):
            n_vols = 40
            stem = f"{sub}_ses-{ses:02d}_task-perception_run-{1 if which == 'A' else 2:02d}"
            bold = os.path.join(base, "func", f"{stem}_bold.nii.gz")
            _save_bold(bold, n_vols, seed=ses * 200 + (1 if which == "A" else 2))
            files.append(bold)
            pair = [pp for pp in S.perception_schedule(p, u) if pp["unit"] == u][0]
            ids = pair["run_A"] if which == "A" else pair["run_B"]
            rows = [{"onset": round(6.0 + i * 6.0, 3), "duration": 4.0, "trial_type": "perception",
                     "identity": vid} for i, vid in enumerate(ids)]
            _write_events(os.path.join(base, "func", f"{stem}_events.tsv"), rows)
    return {"subject": sub, "n_files": len(files), "root": root}
