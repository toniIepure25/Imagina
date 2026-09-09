"""C3XD cue-deconfounding invariants (synthetic + artifact integrity; NO downloads, NO BOLD).
Guards: seal self-hash/timing, artifact self-hashes, acquisition excludes trainPerception,
event contract, cue/imagery/video temporal separation, GLM design construction, synthetic
cue-only vs imagery-only recovery + leakage thresholds, naive-baseline leakage, no semantic/
geometry imports, ROI-provenance fail-closed, decision consistency. CI uses tiny fixtures only.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from app.research.fmri import run_c3xd_design_sim as sim

_ROOT = Path(__file__).resolve().parents[3]
_SEAL = _ROOT / "reports" / "c3xd" / "c3xd_protocol_seal.json"
_HASHED = [
    "reports/c3xd/c3xd_protocol_seal.json",
    "results/c3xd/c3xd_scope_registry.json",
    "results/c3xd/c3xd_event_timing_manifest.json",
    "results/c3xd/raw_acquisition_plan.json",
    "results/c3xd/c3xd_glm_design_selection.json",
    "results/c3xd/c3xd_design_simulation.json",
    "results/c3xd/c3xd_roi_provenance.json",
    "results/c3xd/c3xd_cue_diagnostics.json",
    "results/c3xd/c3xd_raw_imagery_manifest.json",
    "results/c3xd/c3xd_raw_perception_manifest.json",
    "results/c3xd/C3XD_DECISION.json",
]


def _verify(o):
    o = dict(o)
    h = o.pop("self_hash")
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest() == h


def test_seal_present_before_outcomes():
    assert _SEAL.exists()
    o = json.load(open(_SEAL))
    assert _verify(o)
    assert o["sealed_before_neural_or_design_outcomes"] is True
    assert o["not_c4"] and o["no_geometry"] and o["no_reconstruction"]
    assert "insufficient storage" in o["fail_closed_conditions"]


def test_all_artifact_self_hashes():
    for rel in _HASHED:
        p = _ROOT / rel
        if not p.exists():
            continue
        o = json.load(open(p))
        if "self_hash" in o:
            assert _verify(o), rel


def test_acquisition_excludes_trainperception():
    p = _ROOT / "results/c3xd/raw_acquisition_plan.json"
    if not p.exists():
        return
    o = json.load(open(p))
    assert "trainPerception" in o["exclude"]
    assert set(o["tasks"].keys()) == {"testImagery", "testPerception"}
    assert "trainPerception" not in json.dumps(o["tasks"])


def test_event_contract():
    p = _ROOT / "results/c3xd/c3xd_event_timing_manifest.json"
    if not p.exists():
        return
    o = json.load(open(p))
    for s, v in o["subjects"].items():
        assert v["imagery"]["n_trials"] == 360
        assert v["imagery"]["n_videos"] == 72
        assert v["imagery"]["reps_per_video_min"] == 5 and v["imagery"]["reps_per_video_max"] == 5
        assert v["imagery"]["session_balance_ok"] is True
        assert v["perception"]["n_videos"] == 72
        # cue precedes imagery (0 gap) and imagery precedes video (positive gap)
        assert 0.0 in v["imagery"]["cue_to_imagery_gap_unique"]
        assert all(g >= 0 for g in v["imagery"]["imagery_to_video_gap_unique"])


def test_no_semantic_or_geometry_imports():
    src = (Path(sim.__file__).read_text()
           + (_ROOT / "backend/app/research/fmri/run_c3xd_decision.py").read_text()
           + (_ROOT / "backend/app/research/fmri/run_c3xd_event_audit.py").read_text())
    low = src.lower()
    for bad in ("deberta", "timesformer", "c3g_geometry", "participation_ratio",
                "subspace_overlap", "linear_cka", "procrustes", "crossnobis"):
        assert bad not in low, bad
    # case-sensitive tokens (avoid matching np.clip / other lowercase substrings)
    for bad in ("CLIP", "DINO"):
        assert bad not in src, bad


# ---- synthetic design-recovery unit tests (tiny fixture) ----
def _fixture():
    # 2 sessions x 2 videos, one run/session, cue(var dur)->imagery->video->eval
    trials_by_run = []
    for ses in (1, 2):
        run = []
        onset = 10.0
        for vi, vid in enumerate((100, 200)):
            cue_d = 5.0 + 3 * vi
            run.append({"video_id": vid, "cue_onset": onset, "cue_duration": cue_d,
                        "imagery_onset": onset + cue_d, "imagery_duration": 12.0,
                        "video_onset": onset + cue_d + 14.0, "video_duration": 10.0,
                        "eval_onset": onset + cue_d + 26.0, "eval_duration": 6.0, "session": ses, "run": 1})
            onset += cue_d + 40.0
        trials_by_run.append(run)
    return trials_by_run


def test_imagery_only_recovers_and_cue_leaks_less_in_A_than_C():
    trials_by_run = _fixture()
    videos = [t["video_id"] for run in trials_by_run for t in run]
    rng = np.random.default_rng(0)
    gen = sim.spm_hrf()
    fit = sim.spm_hrf()
    # imagery-only -> Model A recovers imagery pattern well
    rA, rB, rC, P_img, _, _ = sim.simulate(trials_by_run, None, videos, 120, gen, fit, 0.5, 0.0, "imagery_only", rng)
    recA = sim._rowcorr(rA, P_img, videos)
    assert recA > 0.5
    # cue+video-only -> Model A cue leakage is lower than naive Model C
    rng2 = np.random.default_rng(1)
    cA, cB, cC, _, P_cue, _ = sim.simulate(trials_by_run, None, videos, 120, gen, fit, 0.5, 0.0, "cuevideo_null", rng2)
    leakA = abs(sim._rowcorr(cA, P_cue, videos))
    leakC = abs(sim._rowcorr(cC, P_cue, videos))
    assert leakC > leakA  # naive late-window leaks the cue more than the separated GLM


def test_design_matrix_imagery_well_conditioned():
    trials_by_run = _fixture()
    n, cue, img, vid, ev = sim.build_run(trials_by_run[0], sim.spm_hrf())
    imgz = (img.T - img.T.mean(0)) / (img.T.std(0) + 1e-12)
    assert np.linalg.cond(imgz) < 5.0  # imagery regressors are not collinear


def test_roi_provenance_failclosed():
    p = _ROOT / "results/c3xd/c3xd_roi_provenance.json"
    if not p.exists():
        return
    assert json.load(open(p))["status"] == "BLOCKED_C3XD_ROI_PROVENANCE"


def test_decision_consistency():
    p = _ROOT / "results/c3xd/C3XD_DECISION.json"
    if not p.exists():
        return
    o = json.load(open(p))
    assert o["decision"] in ("C3XD_BLOCKED_RAW_PIPELINE_INFEASIBLE", "C3XD_BLOCKED_BY_CUE_DECONFOUNDING",
                             "BLOCKED_C3XD_ROI_PROVENANCE", "C3XD_D2_CUE_DECONFOUNDED_IMAGERY_QUALIFIED",
                             "C3XD_D2_CUE_DECONFOUNDED_IMAGERY_LIMITED", "C3XD_D2_RAW_IMAGERY_RELIABILITY_FAIL")
    # a blocked decision must authorize nothing and never C3XE/geometry
    if o["decision"].startswith(("C3XD_BLOCKED", "BLOCKED")):
        assert o["authorizes"] == "nothing (blocked); C3XE preparation NOT authorized"
        for x in ("C3XE", "state geometry", "C4"):
            assert x in o["does_NOT_authorize"]
    assert o["no_geometry_computed"] is True and o["no_raw_neural_data_committed"] is True
    # C3XC preserved
    assert "PRESERVED" in o["c3xc_status"]
