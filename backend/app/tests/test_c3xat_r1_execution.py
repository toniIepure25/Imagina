"""C3XAT-R1 execution-attempt-2 invariants (hermetic; NO cluster/network/BOLD).

Enforces that attempt 2 reuses the sealed C3XAT experiment WITHOUT modification and records an honest,
non-fabricated execution state: prior gates (including the C3XAT seal bb0d07ac...) immutable; the R1
seal designs no new protocol; the fMRIPrep container digest is pinned; no neural outcome is fabricated
while execution is incomplete; the decision is BLOCKED (not FAIL) with the dataset gate unevaluated and
C3XAG unauthorized; the assembler imports no geometry/semantic/reconstruction module; all artifacts
self-hash.
"""
import hashlib
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_R = _ROOT / "results" / "c3xat_r1"
_REP = _ROOT / "reports" / "c3xat_r1"
_C3XAT_SEAL = "bb0d07acb9a2cf8d271d4697acc6cde352b9b12cd38504203b14f8cf6079cee2"
_SUBS = ["S1", "S2", "S3", "S4", "S5", "S6"]
_HASHED = [
    "reports/c3xat_r1/c3xat_r1_execution_seal.json",
    "results/c3xat_r1/cluster_certification.json",
    "results/c3xat_r1/container_provenance.json",
    "results/c3xat_r1/atlas_provenance.json",
    "results/c3xat_r1/dataset_acquisition.json",
    "results/c3xat_r1/C3XAT_R1_DECISION.json",
] + [f"results/c3xat_r1/reliability_{s}.json" for s in _SUBS]


def _verify(o):
    o = dict(o)
    h = o.pop("self_hash")
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest() == h


def _decision():
    return json.load(open(_R / "C3XAT_R1_DECISION.json"))


def test_all_artifact_self_hashes():
    for rel in _HASHED:
        p = _ROOT / rel
        assert p.exists(), rel
        o = json.load(open(p))
        assert "self_hash" in o and _verify(o), rel


def test_prior_gates_and_c3xat_seal_immutable():
    # the C3XAT protocol seal must be byte-identical (self_hash unchanged)
    seal = json.load(open(_ROOT / "reports/c3xat/c3xat_protocol_seal.json"))
    assert seal["self_hash"] == _C3XAT_SEAL
    # attempt-1 decision preserved
    d1 = json.load(open(_ROOT / "results/c3xat/C3XAT_DECISION.json"))
    assert d1["decision"] == "C3XAT_BLOCKED_EXECUTION"
    for rel in ("results/c3xpa/C3XPA_DECISION.json", "reports/c3xdr/c3xdr_execution_seal.json"):
        p = _ROOT / rel
        if p.exists():
            assert _verify(json.load(open(p))), rel


def test_r1_reuses_seal_designs_no_new_protocol():
    seal = json.load(open(_REP / "c3xat_r1_execution_seal.json"))
    assert seal["execution_attempt"] == 2
    assert seal["reuses_c3xat_seal_unchanged"] == _C3XAT_SEAL
    assert seal["designs_new_protocol"] is False
    for frozen in ("dataset", "subjects", "primary_roi", "secondary_roi", "model_a",
                   "reliability_estimator", "permutation", "bootstrap", "seeds",
                   "cue_video_falsification", "dataset_gate"):
        assert frozen in seal["frozen_unchanged"]
    assert _decision()["reuses_c3xat_seal"] == _C3XAT_SEAL


def test_container_digest_pinned():
    c = json.load(open(_R / "container_provenance.json"))
    assert c["fmriprep_digest"].startswith("sha256:") and len(c["fmriprep_digest"]) == 71
    assert c["output_space"] == "MNI152NLin2009cAsym" and c["resolution_mm"] == 2
    assert c["smoothing"] == "NONE"


def test_no_neural_outcome_fabricated_while_incomplete():
    d = _decision()
    assert d["decision"] == "C3XAT_R1_BLOCKED_EXECUTION_INCOMPLETE"
    assert d["is_blocked_not_fail"] is True
    assert d["no_neural_outcome_fabricated"] is True
    assert d["subjects_with_confirmatory_R_I"] == 0
    assert d["dataset_gate_evaluated"] is False
    for s in _SUBS:
        rel = json.load(open(_R / f"reliability_{s}.json"))
        assert rel["status"] == "EXECUTION_INCOMPLETE"
        for k in ("R_I", "perm_p_one_sided", "bootstrap_ci95", "split_seed_min", "R_P", "cue_gain",
                  "video_gain", "R_I_cuevideo_predicted", "Delta_I", "subject_pass_status"):
            assert rel[k] is None, (s, k)


def test_infra_pass_but_c3xag_not_authorized():
    d = _decision()
    assert d["infrastructure_gate"] == "C3XAT_R1_REMOTE_INFRA_PASS"
    assert d["c3xag_authorized"] is False
    for bad in ("C3XAG execution", "C3XE", "C3XR", "C4", "geometry", "decoding", "reconstruction"):
        assert bad in d["does_NOT_authorize"]


def test_dataset_contract_matches_sealed_experiment():
    a = json.load(open(_R / "dataset_acquisition.json"))
    assert a["version"] == "1.0.2"
    assert a["imagery_sessions_count"] == 5
    assert a["trainPerception_excluded_from_analysis_and_tuning"] is True
    assert len(a["subjects_present"]) == 6
    assert all("trainPerception" in x for x in a["bids_layout"]["excluded_train_sessions"])


def test_assembler_is_measurement_only_no_forbidden_imports():
    src = (_ROOT / "backend/app/research/fmri/run_c3xat_r1_execute.py").read_text()
    imports = "\n".join(ln for ln in src.splitlines()
                        if ln.strip().startswith(("import ", "from "))).lower()
    for bad in ("c3g_geometry", "participation_ratio", "subspace_overlap", "linear_cka", "procrustes",
                "state_transport", "deberta", "timesformer", "stable_diffusion", "reconstruct",
                "nibabel", "nilearn", "clip", "dino", "torch", "transformers"):
        assert bad not in imports, bad


def test_no_credentials_committed():
    # the decision/cluster artifacts must assert credentials are not committed, and no kubeconfig/
    # license/token content should appear in the committed JSON
    d = _decision()
    assert d["credentials_committed"] is False
    cl = json.load(open(_R / "cluster_certification.json"))
    assert cl["freesurfer_license"]["committed_to_git"] is False
    blob = json.dumps(d) + json.dumps(cl)
    for secretish in ("BEGIN RSA", "BEGIN PRIVATE", "client-certificate-data", "client-key-data",
                      "token:", "password"):
        assert secretish not in blob


# --- continuation of execution attempt 2 (acquisition complete, atlas resolved, fMRIPrep running) ---

def _load(name):
    return json.load(open(_R / name))


def test_new_resolved_artifacts_self_hash():
    for name in ("C3XAT_R1_STATUS_CLARIFICATION.json", "atlas_provenance_resolved.json",
                 "execution_progress.json"):
        p = _R / name
        if p.exists():
            assert _verify(_load(name)), name


def test_status_clarification_is_administrative_and_seals_unchanged():
    p = _R / "C3XAT_R1_STATUS_CLARIFICATION.json"
    if not p.exists():
        return
    c = _load("C3XAT_R1_STATUS_CLARIFICATION.json")
    assert c["interpretation"] == "INTERIM_EXECUTION_CHECKPOINT"
    assert c["attempt_closed"] is False and c["continue_same_attempt"] is True
    assert c["execution_attempt"] == 2
    assert c["modifies_scientific_seal"] is False
    assert c["c3xat_seal_unchanged"] == _C3XAT_SEAL
    # the historical interim checkpoint must still exist unchanged
    assert json.load(open(_R / "C3XAT_R1_DECISION.json"))["decision"] == "C3XAT_R1_BLOCKED_EXECUTION_INCOMPLETE"


def test_acquisition_manifest_exact_no_approximate_values():
    p = _R / "acquisition_manifest.json"
    if not p.exists():
        return
    m = _load("acquisition_manifest.json")
    s = m["summary"]
    assert isinstance(s["total_bytes"], int) and s["total_bytes"] > 0
    assert s["n_files"] == len(m["files"])
    assert s["zero_byte_files"] == []              # no partial files
    assert s["trainPerception_in_subset"] is False  # trainPerception excluded from analysis subset
    assert len(s["subjects"]) == 6
    for sub, inv in s["inventory"].items():
        assert len(inv["imagery"]) == 5            # 5 imagery sessions each
        assert inv["train_present"] == []
    # every acquired file carries an exact sha256 and byte count (no '~' approximations)
    for f in m["files"][:50]:
        assert isinstance(f["bytes"], int) and len(f["sha256"]) == 64


def test_atlas_provenance_resolved_real_hashes_complete_mpm():
    p = _R / "atlas_provenance_resolved.json"
    if not p.exists():
        return
    a = _load("atlas_provenance_resolved.json")
    assert a["status"] == "ATLAS_SPACE_PROVENANCE_RESOLVED"
    w = a["wang2015"]
    assert w["complete_mpm"] is True and w["maps"] == 25 and w["both_hemispheres"] is True
    assert w["no_performance_subselection"] is True
    for f in w["maxprob_label_files"]:
        assert len(f["sha256"]) == 64             # real resolved hash, not null
    t = a["target_space_transform"]
    assert t["target_template"] == "MNI152NLin2009cAsym" and t["target_res_mm"] == 2
    assert t["source_template"] == "MNI152NLin6Asym"
    assert len(t["sha256"]) == 64                 # transform hashed
    assert t["custom_registration"] is False and t["result_driven_spatial_adjustment"] is False
    assert "label-safe" in t["interpolation"]
    assert a["c3xat_seal"] == _C3XAT_SEAL


def test_execution_progress_running_but_no_fabricated_R_I():
    p = _R / "execution_progress.json"
    if not p.exists():
        return
    e = _load("execution_progress.json")
    assert e["execution_attempt"] == 2
    assert e["acquisition"]["status"] == "COMPLETE"
    assert e["confirmatory_measurement"]["R_I_computed"] is False
    assert e["confirmatory_measurement"]["fabricated"] is False
    assert e["dataset_gate_evaluated"] is False
    assert e["c3xag_authorized"] is False
    assert e["container"]["frozen"] is True


# ---- atlas-space provenance blocker (final decision for attempt 2) ---------------------------------
def test_atlas_space_provenance_blocker_consistency():
    p = _R / "atlas_space_provenance_blocker.json"
    if not p.exists():
        return
    b = json.load(open(p))
    assert _verify(b)
    assert b["is_genuine_fail_closed_blocker"] is True
    assert b["no_neural_outcome_inspected"] is True
    # transform was resolved+hashed; only the volumetric Wang MPM source is missing
    assert "2e3869a0" in b["transform_and_reference_status"]


def test_final_decision_blocked_not_fail_and_no_fabrication():
    p = _R / "C3XAT_R1_FINAL_DECISION.json"
    if not p.exists():
        return
    d = json.load(open(p))
    assert _verify(d)
    if d["decision"].startswith("C3XAT_R1_BLOCKED"):
        assert d["is_blocked_not_fail"] is True
        assert d["dataset_gate_evaluated"] is False
        assert d["primary_wang25_roi_constructed"] is False
        assert d["no_neural_outcome_fabricated"] is True
        assert d["implementation_freeze_written"] is False
        assert d["c3xag_authorized"] is False
        assert d["pass_count_of_6"] is None
        assert all(v is None for v in d["per_subject_R_I"].values())
        # interim checkpoint superseded but preserved, seals unchanged
        assert d["supersedes_interim_execution_checkpoint"] == "C3XAT_R1_BLOCKED_EXECUTION_INCOMPLETE"
        assert d["seals_unchanged"] is True and d["not_c3xat_r2"] is True
        assert d["c3xat_seal"] == _C3XAT_SEAL
    # the interim checkpoint file itself must still exist unchanged
    interim = _R / "C3XAT_R1_DECISION.json"
    if interim.exists():
        assert json.load(open(interim))["decision"] == "C3XAT_R1_BLOCKED_EXECUTION_INCOMPLETE"


# ---- perception-estimand blocker (successor terminal decision, attempt 2) --------------------------
def test_perception_estimand_blocker_preoutcome():
    p = _R / "perception_run_split_coverage_preoutcome.json"
    if not p.exists():
        return
    cov = json.load(open(p))
    assert _verify(cov)
    # if any 5v5 split has <72 common videos, R_P must be unauthorized (no outcome used)
    if not cov.get("all_subjects_all_splits_72_common", True):
        assert cov["R_P_authorized"] is False
        assert cov["blocked_decision"] == "C3XAT_R1_BLOCKED_PERCEPTION_ESTIMAND"
        assert cov["no_workaround_applied"]["outcome_guided"] is False


def test_perception_bug_detected_preoutcome_no_outcome_used():
    p = _R / "confirmatory_driver_perception_bug_preoutcome.json"
    if not p.exists():
        return
    b = json.load(open(p))
    assert _verify(b)
    assert b["detected_before_outcome_inspection"] is True
    assert b["scientific_outcome_used_for_detection"] is False
    assert b["invalid_outputs_quarantined"] is True


def test_final_decision_v2_blocked_no_fabrication():
    p = _R / "C3XAT_R1_FINAL_DECISION_v2.json"
    if not p.exists():
        return
    d = json.load(open(p))
    assert _verify(d)
    if d["decision"] == "C3XAT_R1_BLOCKED_PERCEPTION_ESTIMAND":
        assert d["is_blocked_not_fail"] is True
        assert d["dataset_gate_evaluated"] is False
        assert d["no_neural_outcome_computed_or_inspected"] is True
        assert d["R_P_authorized"] is False
        assert d["c3xag_authorized"] is False
        assert d["seals_unchanged"] is True and d["not_c3xat_r2"] is True
        assert d["c3xat_seal"] == _C3XAT_SEAL
    # prior atlas-blocked final decision preserved unchanged
    prior = _R / "C3XAT_R1_FINAL_DECISION.json"
    if prior.exists():
        assert json.load(open(prior))["decision"] == "C3XAT_R1_BLOCKED_ATLAS_SPACE_PROVENANCE"


# ---- perception estimand resolution + freeze v2 (successor, attempt 2) ------------------------------
def test_perception_runpair_contract_and_resolution():
    p = _R / "perception_runpair_contract_preoutcome.json"
    if not p.exists():
        return
    c = json.load(open(p))
    assert _verify(c)
    assert c["outcome_inspected"] is False
    if c.get("all_subjects_pass"):
        for _s, subj in c["per_subject"].items():
            assert subj["n_run_pairs"] == 5
            assert subj["all_pairs_72_exact"] and subj["all_pairs_disjoint_within_pair"]
            assert subj["all_videos_5_repetitions"] and subj["subject_contract_pass"]
        res = _R / "C3XAT_R1_PERCEPTION_ESTIMAND_BLOCKER_RESOLUTION.json"
        if res.exists():
            r = json.load(open(res))
            assert _verify(r)
            assert r["resolution"] == "FIXED_72_VIDEO_PERCEPTION_RUNPAIR_ESTIMAND_CERTIFIED"
            assert r["outcome_inspected"] is False
            assert r["original_seals_changed"] is False and r["C3XAT_R2"] is False
            assert all(v is False for v in r["no_workaround_used"].values())


def test_perception_estimand_seal_and_five_runpair():
    seal = _R / "perception_runpair_estimand_preoutcome_seal.json"
    if seal.exists():
        s = json.load(open(seal))
        assert _verify(s)
        assert s["name"] == "R_P_RUNPAIR" and s["independent_unit"] == "PERCEPTION RUN-PAIR"
        assert s["n_independent_units"] == 5
        assert s["estimator_callable"].startswith("c3xb_reliability.reliability_with_inference_pairs")
        assert s["neural_outcomes_used"] == "NONE"
    clar = _R / "perception_five_runpair_estimator_clarification.json"
    if clar.exists():
        c = json.load(open(clar))
        assert _verify(c)
        assert c["scientific_estimator_code_changed"] is False


def test_atlas_qc_all_subjects_and_mask_frozen():
    p = _R / "atlas_qc_all_subjects_preoutcome.json"
    if not p.exists():
        return
    q = json.load(open(p))
    assert _verify(q)
    assert q["primary_mask_sha256"] == "19b681ecba5c8d2aa323b8f6e15d36191d4036cea070d095663a790690c544fc"
    assert q["primary_voxels"] == 7604
    assert q["roi_not_intersected_with_brainmask"] is True and q["roi_not_eroded_dilated"] is True
    if q.get("all_subjects_atlas_qc_pass"):
        for _s, v in q["per_subject"].items():
            assert v["shape_match"] and v["affine_match"] and v["roi_voxels_ok"]
            assert v["roi_finite_bold_fraction"] == 1.0 and v["atlas_qc_pass"] is True


def test_implementation_freeze_v2_preoutcome():
    p = _R / "implementation_freeze_manifest_v2.json"
    if not p.exists():
        return
    m = json.load(open(p))
    assert _verify(m)
    assert m["real_R_I_before_v2_freeze"] is False
    assert m["real_R_P_before_v2_freeze"] is False
    assert m["real_Delta_before_v2_freeze"] is False
    assert m["imagery_scientific_pipeline_changed"] is False
    assert m["atlas_changed"] is False and m["estimator_changed"] is False
    assert m["threshold_changed"] is False and m["dataset_gate_changed"] is False
    assert m["perception_unit"] == "RUN-PAIR (R_P_RUNPAIR)"
    assert m["seals_unchanged"] is True and m["not_c3xat_r2"] is True
    assert m["c3xat_seal"] == _C3XAT_SEAL
    # v1 freeze preserved unchanged
    v1 = _R / "implementation_freeze_manifest.json"
    if v1.exists():
        assert json.load(open(v1))["artifact"] == "C3XAT_R1_IMPLEMENTATION_FREEZE_MANIFEST"


# ---- primary dataset decision (LIMITED, frozen) + secondary cannot change it -----------------------
def test_primary_dataset_decision_limited_1of6():
    p = _R / "C3XAT_R1_PRIMARY_DATASET_DECISION.json"
    if not p.exists():
        return
    d = json.load(open(p))
    assert _verify(d)
    assert d["primary_dataset_decision"] == "C3XAT_D2_ATLAS_IMAGERY_LIMITED"
    assert d["pass_count"] == 1 and d["n_subjects"] == 6
    passing = [s for s, v in d["per_subject"].items() if v["primary_pass"]]
    assert passing == ["sub-03"]                       # sub-03 is the ONLY primary PASS
    # sub-02 reliable imagery+perception but Delta fails -> NOT promoted
    s2 = d["per_subject"]["sub-02"]
    assert s2["imagery_pass"] is True and s2["perception_pass"] is True
    assert s2["cuevideo_pass"] is False and s2["primary_pass"] is False
    assert d["qualified"] is False and d["c3xag_preparation_authorized"] is False
    assert d["no_subject_dropped"] is True and d["frozen_before_secondary"] is True


def test_secondary_cannot_change_primary():
    s = _R / "C3XAT_R1_SECONDARY_RESULTS.json"
    if not s.exists():
        return
    o = json.load(open(s))
    assert _verify(o)
    assert o["primary_decision_changed"] is False
    assert o["primary_decision"] == "C3XAT_D2_ATLAS_IMAGERY_LIMITED"
    assert o["pass_count"] == "1/6"
    assert o["c3xag_authorized"] is False


def test_final_decision_complete_limited():
    p = _R / "C3XAT_R1_FINAL_DECISION_COMPLETE.json"
    if not p.exists():
        return
    d = json.load(open(p))
    assert _verify(d)
    assert d["final_decision"] == "C3XAT_D2_ATLAS_IMAGERY_LIMITED"
    assert d["pass_count"] == "1/6" and d["only_primary_pass"] == "sub-03"
    assert d["c3xag_preparation_authorized"] is False
    assert d["seals_unchanged"] is True and d["not_c3xat_r2"] is True
    assert d["c3xat_seal"] == _C3XAT_SEAL
    # historical decisions preserved (unchanged files still present)
    for hist in ("C3XAT_R1_DECISION.json", "C3XAT_R1_FINAL_DECISION.json",
                 "C3XAT_R1_FINAL_DECISION_v2.json", "C3XAT_R1_PRIMARY_DATASET_DECISION.json"):
        assert (_R / hist).exists()


def test_final_integrity_audit_passes():
    p = _R / "final_integrity_audit.json"
    if not p.exists():
        return
    a = json.load(open(p))
    assert _verify(a)
    assert a["all_pass"] is True
    assert a["primary_decision"] == "C3XAT_D2_ATLAS_IMAGERY_LIMITED"
    assert a["c3xag_authorized"] is False
    assert a["no_raw_neural_data_committed"] is True
