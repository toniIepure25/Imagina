"""C3XDR execution-rerun invariants (hermetic; NO downloads, NO BOLD). Guards the execution
seal, C3XD lineage, immutability of prior gates, trainPerception exclusion, Model-A freeze,
ROI/decision fail-closed contracts, artifact self-hashes, and the no-semantic/no-geometry rules.
"""
import hashlib
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SEAL = _ROOT / "reports" / "c3xdr" / "c3xdr_execution_seal.json"
_HASHED = [
    "reports/c3xdr/c3xdr_execution_seal.json",
    "results/c3xdr/infrastructure_audit.json",
    "results/c3xdr/raw_acquisition_manifest.json",
    "results/c3xdr/c3xdr_preprocessing_spec.json",
    "results/c3xdr/c3xdr_roi_provenance.json",
    "results/c3xdr/c3xdr_imagery_manifest.json",
    "results/c3xdr/c3xdr_perception_manifest.json",
    "results/c3xdr/c3xdr_cue_magnitude.json",
    "results/c3xdr/c3xdr_cuevideo_falsification.json",
    "results/c3xdr/c3xdr_temporal_controls.json",
    "results/c3xdr/C3XDR_DECISION.json",
] + [f"results/c3xdr/c3xdr_reliability_S{i}.json" for i in range(1, 7)]

_C3XD_SEAL_HASH = "1a680c1b1d2e3f0c015bae41088f3a5a97642ff119e9a52b995e1f3c66a723fb"


def _verify(o):
    o = dict(o)
    h = o.pop("self_hash")
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest() == h


def test_seal_self_hash_and_lineage():
    assert _SEAL.exists()
    o = json.load(open(_SEAL))
    assert _verify(o)
    assert o["is_execution_rerun_not_new_hypothesis"] is True
    assert o["not_c3xe"] and o["not_c4"] and o["no_geometry"] and o["no_reconstruction"]
    assert o["lineage"]["c3xd_seal_self_hash"] == _C3XD_SEAL_HASH
    assert o["lineage"]["c3xd_final_sha"] == "d60cbfde4cab53270298f4b0df59e3beb8cfddab"


def test_all_artifact_self_hashes():
    for rel in _HASHED:
        p = _ROOT / rel
        if not p.exists():
            continue
        o = json.load(open(p))
        if "self_hash" in o:
            assert _verify(o), rel


def test_prior_gate_seals_immutable():
    # C3XD and C3XC seals still verify with their committed self-hashes (not rewritten by C3XDR)
    for rel in ("reports/c3xd/c3xd_protocol_seal.json", "reports/c3xc/c3xc_protocol_seal.json"):
        o = json.load(open(_ROOT / rel))
        assert _verify(o), rel
    d = json.load(open(_ROOT / "reports/c3xd/c3xd_protocol_seal.json"))
    assert d["self_hash"] == _C3XD_SEAL_HASH


def test_trainperception_excluded():
    o = json.load(open(_SEAL))
    assert "trainPerception" in o["selective_acquisition"]["exclude"]
    assert "trainPerception" not in json.dumps(o["selective_acquisition"]["include"])
    p = _ROOT / "results/c3xdr/raw_acquisition_manifest.json"
    if p.exists():
        m = json.load(open(p))
        assert "trainPerception" not in json.dumps(m.get("planned_subset", {}).get("include", []))
        assert m["downloaded_bytes"] == 0  # nothing downloaded before the gate passed


def test_model_A_frozen_and_not_outcome_selected():
    o = json.load(open(_SEAL))
    pe = o["primary_estimator_frozen"]
    assert pe["model"] == "MODEL_A_LSA"
    assert pe["frozen_before_raw_outcome"] is True
    assert o["integrity"]["no_outcome_based_model_or_roi_or_subject_or_trial_selection"] is True
    dec = _ROOT / "results/c3xdr/C3XDR_DECISION.json"
    if dec.exists():
        assert json.load(open(dec))["model_selection_touched_real_bold"] is False


def test_roi_and_contracts_frozen():
    o = json.load(open(_SEAL))
    assert o["roi_contract"]["primary"].startswith("VC")
    assert o["roi_contract"]["fail_closed"] == "C3XDR_BLOCKED_ROI_PROVENANCE"
    assert o["contracts"]["imagery"]["trials"] == 360
    assert o["contracts"]["imagery"]["videos"] == 72
    assert o["contracts"]["imagery"]["reps_per_video"] == 5
    assert o["contracts"]["correspondence"].startswith("72/72")


def test_no_semantic_or_geometry_imports():
    src = (_ROOT / "backend/app/research/fmri/run_c3xdr_decision.py").read_text()
    low = src.lower()
    for bad in ("deberta", "timesformer", "c3g_geometry", "participation_ratio", "subspace_overlap",
                "linear_cka", "procrustes", "crossnobis", "nilearn"):
        assert bad not in low, bad
    for bad in ("CLIP", "DINO"):
        assert bad not in src, bad


def test_decision_blocked_authorizes_nothing():
    p = _ROOT / "results/c3xdr/C3XDR_DECISION.json"
    if not p.exists():
        return
    o = json.load(open(p))
    assert o["decision"].startswith("C3XDR_BLOCKED") or o["decision"].startswith("C3XDR_D2_")
    if o["decision"].startswith("C3XDR_BLOCKED"):
        assert o["is_blocked_not_fail"] is True
        assert o["raw_reliability_gate_evaluated"] is False
        assert o["subjects_processed"] == 0
        assert o["downloaded_bytes"] == 0
        assert o["authorizes"] == "nothing (blocked); C3XE preparation NOT authorized"
        for x in ("C3XE", "state geometry", "C4"):
            assert x in o["does_NOT_authorize"]
    assert o["no_geometry_computed"] and o["no_raw_neural_data_committed"]
    assert "PRESERVED" in o["c3xc_status"] and "PRESERVED" in o["c3xd_status"]


def test_infrastructure_gate_requirement():
    p = _ROOT / "results/c3xdr/infrastructure_audit.json"
    if not p.exists():
        return
    o = json.load(open(p))
    # gate requires >=300 GB; the audit must honestly report whether it is met
    assert o["requirement"]["min_usable_persistent_storage_GB"] == 300
    if not o["requirement_met"]:
        assert o["status"] == "C3XDR_BLOCKED_STORAGE"
        assert o["best_free_GB"] < 300
