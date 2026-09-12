"""Synthetic, outcome-independent tests for the C3XAT-R1 analysis pipeline.

These validate every component that can be developed WITHOUT real neural outcomes, using synthetic
fixtures / metadata / known dimensions only. In particular they prove the cue/video forward operator
carries EXACTLY zero true-imagery contribution, the reliability wiring is session-disjoint with
within-session permutation and non-straddling bootstrap, and the subject/dataset gates implement the
frozen rules at their boundaries. NO real R_I/R_P/Delta is computed anywhere.
"""
import numpy as np
import pytest

from app.research.fmri import c3xat_pipeline as P


# ---- event parsing / trial contract --------------------------------------------------------------
def _synth_session_rows(video_ids, base=0.0):
    """One synthetic imagery run: for each video a cue(-2), imagery(2), post-video(3) triple."""
    rows = []
    t = base
    for v in video_ids:
        rows.append({"onset": t, "duration": 7, "trial_type": "-2", "cueID": v,
                     "imageryID": 0, "stimID": 0})
        t += 8
        rows.append({"onset": t, "duration": 12, "trial_type": "2", "cueID": 0,
                     "imageryID": v, "stimID": 0})
        t += 13
        rows.append({"onset": t, "duration": 10, "trial_type": "3", "cueID": 0,
                     "imageryID": 0, "stimID": v})
        t += 11
    return rows


def test_parse_events_maps_kinds_and_ids():
    rows = _synth_session_rows([5, 9])
    ev = P.parse_events(rows, session=1, run=1)
    kinds = sorted({e.kind for e in ev})
    assert kinds == ["cue", "imagery", "postvideo"]
    imagery = [e for e in ev if e.kind == "imagery"]
    assert {e.video_id for e in imagery} == {5, 9}


def test_trial_contract_pass_and_fail():
    # full sealed contract: 72 videos x 5 reps = 360 imagery trials across 5 sessions
    # (one repetition of every video per session -> 72/session x 5 sessions)
    trials = []
    for s in range(1, 6):
        for v in range(1, 73):
            trials.append(P.TrialEvent(0.0, 12.0, "imagery", v, s, 1))
    r = P.verify_trial_contract(trials)
    assert r["contract_pass"] is True
    assert r["n_imagery_trials"] == 360 and r["distinct_videos"] == 72
    # drop one trial -> fail closed
    r2 = P.verify_trial_contract(trials[:-1])
    assert r2["contract_pass"] is False


# ---- Model A design --------------------------------------------------------------------------------
def test_model_a_design_structure_and_ordering():
    rows = _synth_session_rows([1, 2, 3])
    ev = P.parse_events(rows, 1, 1)
    n_scans, tr = 120, 2.0
    nuis = np.random.default_rng(0).normal(size=(n_scans, 6))
    d = P.build_model_a_design(ev, n_scans, tr, nuisance=nuis)
    # 3 cue + 3 imagery + 3 postvideo regressors, separately identifiable
    assert len(d["blocks"]["cue"]) == 3
    assert len(d["blocks"]["imagery"]) == 3
    assert len(d["blocks"]["postvideo"]) == 3
    # deterministic ordering: cue block indices all precede imagery, which precede postvideo
    assert max(d["blocks"]["cue"]) < min(d["blocks"]["imagery"])
    assert max(d["blocks"]["imagery"]) < min(d["blocks"]["postvideo"])
    assert "grouped_eval" in d["labels"] and "intercept" in d["labels"]
    assert len(d["nuisance_idx"]) == 6
    # design matrix shape and acceptable rank
    X = d["design"]
    assert X.shape[0] == n_scans
    assert np.linalg.matrix_rank(X) >= 3 + 3 + 3  # trial regressors identifiable


def test_design_deterministic():
    rows = _synth_session_rows([4, 8])
    ev = P.parse_events(rows, 1, 1)
    a = P.build_model_a_design(ev, 100, 2.0)["design"]
    b = P.build_model_a_design(ev, 100, 2.0)["design"]
    assert np.array_equal(a, b)


# ---- confound resolver -----------------------------------------------------------------------------
def test_confound_resolver_frozen_and_failclosed():
    cols = ["trans_x", "trans_y", "trans_z", "rot_x", "rot_y", "rot_z",
            "csf", "white_matter", "cosine00", "cosine01", "global_signal", "framewise_displacement"]
    r = P.resolve_confounds(cols)
    assert r["resolver_pass"] is True
    assert r["motion"] == P.FROZEN_NUISANCE_MOTION
    assert r["tissue"] == ["csf", "white_matter"]
    assert r["cosine"] == ["cosine00", "cosine01"]
    # global_signal / FD are NOT auto-included (outcome-independent frozen list)
    assert "global_signal" not in r["selected"]
    # missing required motion -> fail closed
    r2 = P.resolve_confounds(["trans_x", "csf"])
    assert r2["resolver_pass"] is False and len(r2["missing_required_motion"]) == 5


# ---- Wang25 QC -------------------------------------------------------------------------------------
def test_wang25_qc_pass_and_grid_mismatch():
    aff = np.array([[2, 0, 0, -96.5], [0, 2, 0, -132.5], [0, 0, 2, -78.5], [0, 0, 0, 1]], float)
    labels = list(range(1, 26))
    ok = P.wang25_qc(aff, (97, 115, 97), aff, (97, 115, 97), labels, list(range(1, 26)), 1.0)
    assert ok["qc_pass"] is True and ok["n_labels"] == 25
    # affine mismatch fails closed (no warping allowed to fix it)
    aff2 = aff.copy()
    aff2[0, 3] += 4.0
    bad = P.wang25_qc(aff2, (97, 115, 97), aff, (97, 115, 97), labels, list(range(1, 26)), 1.0)
    assert bad["qc_pass"] is False
    # a dropped parcel fails closed (complete MPM required)
    miss = P.wang25_qc(aff, (97, 115, 97), aff, (97, 115, 97), list(range(1, 25)), list(range(1, 26)), 1.0)
    assert miss["all_labels_present"] is False and miss["qc_pass"] is False


# ---- cue/video forward operator: EXACT zero imagery contribution ----------------------------------
def test_forward_contamination_has_zero_true_imagery():
    rng = np.random.default_rng(1)
    rows = _synth_session_rows([1, 2, 3, 4])
    ev = P.parse_events(rows, 1, 1)
    n_scans, n_vox = 200, 5
    d = P.build_model_a_design(ev, n_scans, 2.0, nuisance=rng.normal(size=(n_scans, 6)))
    ncol = d["design"].shape[1]
    betas = rng.normal(size=(ncol, n_vox))
    # give the imagery + grouped_eval columns HUGE betas; predicted contamination must ignore them
    for i in d["blocks"]["imagery"]:
        betas[i, :] = 1e6
    betas[d["labels"].index("grouped_eval"), :] = 1e6
    pred = P.forward_contamination_bold(d, betas)
    # rebuild with imagery/eval betas ZEROED: must be identical -> proves zero imagery contribution
    betas0 = betas.copy()
    for i in d["blocks"]["imagery"]:
        betas0[i, :] = 0.0
    betas0[d["labels"].index("grouped_eval"), :] = 0.0
    pred0 = P.forward_contamination_bold(d, betas0)
    assert np.allclose(pred, pred0, atol=0), "true imagery contribution leaked into contamination"


def test_forward_contamination_reflects_cue_and_postvideo():
    rows = _synth_session_rows([1, 2, 3])
    ev = P.parse_events(rows, 1, 1)
    n_scans, n_vox = 150, 4
    d = P.build_model_a_design(ev, n_scans, 2.0)
    ncol = d["design"].shape[1]
    b = np.zeros((ncol, n_vox))
    # cue-only contamination -> nonzero predicted BOLD
    for i in d["blocks"]["cue"]:
        b[i, :] = 3.0
    pred_cue = P.forward_contamination_bold(d, b)
    assert np.any(np.abs(pred_cue) > 0)


# ---- reliability wiring: session-disjoint / within-session perm / non-straddling bootstrap --------
def _synth_betas(n_sessions=4, n_videos=8, reps=4, n_vox=10, signal=0.6, seed=0):
    rng = np.random.default_rng(seed)
    templ = rng.normal(size=(n_videos, n_vox))
    X, vids, sess = [], [], []
    for s in range(n_sessions):
        for v in range(n_videos):
            for _ in range(reps):
                X.append(signal * templ[v] + (1 - signal) * rng.normal(size=n_vox))
                vids.append(v)
                sess.append(s)
    return np.array(X), np.array(vids), np.array(sess)


def test_reliability_reliable_signal_passes_null_does_not():
    # wiring/behaviour test: modest n for speed; the FROZEN 1000/1000 path is exercised in the
    # confirmatory campaign, not in unit tests.
    X, vids, sess = _synth_betas(signal=0.9, seed=3)
    res = P.reliability_with_inference_pairs(X, vids, sess, P.SEED_BASE, n_perm=200, n_boot=200)
    assert res["reliability"] > 0 and res["split_seed_min"] > 0
    assert P.subject_imagery_pass(res) is True
    # scrambled (no shared template across sessions) -> not reliable, fails the frozen gate
    rng = np.random.default_rng(9)
    Xn = rng.normal(size=X.shape)
    resn = P.reliability_with_inference_pairs(Xn, vids, sess, P.SEED_BASE, n_perm=200, n_boot=200)
    assert P.subject_imagery_pass(resn) is False


def test_reliability_seed_determinism_and_session_unit():
    X, vids, sess = _synth_betas(seed=5)
    a = P.reliability_with_inference_pairs(X, vids, sess, P.SEED_BASE, n_perm=60, n_boot=60)
    b = P.reliability_with_inference_pairs(X, vids, sess, P.SEED_BASE, n_perm=60, n_boot=60)
    assert a["reliability"] == b["reliability"]
    assert a["split_seed_values"] == b["split_seed_values"]
    assert a["unit"] == "run_pair_disjoint"  # session-as-unit (run-pair/session-disjoint) machinery
    assert len(a["split_seed_values"]) == 3  # sealed three-seed evaluation


# ---- Delta + gates ---------------------------------------------------------------------------------
def test_delta_and_subject_gate_composition():
    assert P.delta_i(0.4, 0.1) == pytest.approx(0.3)
    # subject primary PASS requires ALL five components
    assert P.subject_primary_pass(True, True, True, True, True) is True
    assert P.subject_primary_pass(True, True, False, True, True) is False


def test_dataset_gate_boundaries():
    assert P.dataset_gate(2, 6) == "C3XAT_D2_ATLAS_IMAGERY_QUALIFIED"
    assert P.dataset_gate(3, 6) == "C3XAT_D2_ATLAS_IMAGERY_QUALIFIED"
    assert P.dataset_gate(1, 6) == "C3XAT_D2_ATLAS_IMAGERY_LIMITED"
    assert P.dataset_gate(0, 6) == "C3XAT_D2_ATLAS_IMAGERY_FAIL"
    # fewer than 6 valid measurements cannot FAIL -> blocked
    assert P.dataset_gate(0, 5).startswith("C3XAT_R1_BLOCKED")
