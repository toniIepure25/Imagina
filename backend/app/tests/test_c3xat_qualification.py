"""C3XAT atlas-defined raw imagery qualification invariants (hermetic; NO cluster/network/BOLD).

Enforces the C3XAT seal and closeout WITHOUT downloading ds005191 or inspecting any neural outcome:
prior gates immutable; C3XAT is a new family, not a C3XDR replay; Wang25 complete MPM is primary with no
performance subselection; Benson V1-V3 is secondary and cannot rescue the primary gate; MNI target space
and atlas hash provenance are pinned; no smoothing unless sealed; Model A is unchanged; the 72-video /
360-trial / 5-session contract holds; the reliability estimator is the frozen session-disjoint
c3xb_reliability callable using within-session permutation, a non-straddling bootstrap, and split-seed
robustness; cue/video falsification is mandatory; no semantic features / no geometry / no reconstruction;
the >=2/6 dataset rule is sealed; and the blocked closeout fabricates no outcome.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[3]
_R = _ROOT / "results" / "c3xat"
_REP = _ROOT / "reports" / "c3xat"
_C3XDR_SEAL = "7afc79466c75b671865fc787a56e8e421b4774bfd3d2b65b133092450302f43d"
_SUBS = ["S1", "S2", "S3", "S4", "S5", "S6"]
_HASHED = [
    "reports/c3xat/c3xat_protocol_seal.json",
    "results/c3xat/c3xat_scope_registry.json",
    "results/c3xat/dataset_contract.json",
    "results/c3xat/preprocessing_provenance.json",
    "results/c3xat/wang2015_atlas_provenance.json",
    "results/c3xat/benson14_atlas_provenance.json",
    "results/c3xat/infrastructure_reaudit.json",
    "results/c3xat/perception_reliability.json",
    "results/c3xat/cuevideo_falsification.json",
    "results/c3xat/negative_controls.json",
    "results/c3xat/secondary_benson_results.json",
    "results/c3xat/spatial_enrichment_control.json",
    "results/c3xat/C3XAT_DECISION.json",
] + [f"results/c3xat/roi_qc_{s}.json" for s in _SUBS] \
  + [f"results/c3xat/reliability_{s}.json" for s in _SUBS]


def _verify(o):
    o = dict(o)
    h = o.pop("self_hash")
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest() == h


def _seal():
    return json.load(open(_REP / "c3xat_protocol_seal.json"))


def _decision():
    return json.load(open(_R / "C3XAT_DECISION.json"))


def test_all_artifact_self_hashes():
    for rel in _HASHED:
        p = _ROOT / rel
        assert p.exists(), rel
        o = json.load(open(p))
        assert "self_hash" in o and _verify(o), rel


def test_prior_gates_immutable():
    for rel in ("results/c3xpa/C3XPA_DECISION.json", "results/c3xpr/C3XPR_DECISION.json",
                "results/c3xdr_r1/C3XDR_R1_DECISION.json", "reports/c3xdr/c3xdr_execution_seal.json"):
        p = _ROOT / rel
        if p.exists():
            assert _verify(json.load(open(p))), rel
    s = _ROOT / "reports/c3xdr/c3xdr_execution_seal.json"
    if s.exists():
        assert json.load(open(s))["self_hash"] == _C3XDR_SEAL
    # C3XAT must not silently claim to supersede anything
    scope = json.load(open(_R / "c3xat_scope_registry.json"))
    assert scope["no_historical_decision_superseded"] is True


def test_c3xat_is_not_c3xdr_replay():
    seal = _seal()
    assert seal["not_c3xdr_replay"] is True
    assert seal["not_exact_kamitani_roi"] is True
    d = _decision()
    assert d["c3xdr_rescued"] is False
    assert d["kamitani_roi_replicated"] is False
    assert seal["lineage"]["c3xdr_seal_unchanged"] == _C3XDR_SEAL


def test_wang25_is_primary_complete_no_fishing():
    pr = _seal()["frozen"]["primary_roi"]
    assert pr["name"] == "WANG25_TOPOGRAPHIC_VISUAL_NETWORK"
    assert pr["use_complete_atlas"] is True
    assert pr["no_subselection_by_performance"] is True
    assert pr["maps"] == 25 and pr["regions"] == 22
    # named as an atlas network, never adopted as the Kamitani "VC" label
    assert "atlas-defined topographic visual network" in pr["terminology"]
    assert pr["name"] != "VC" and "Kamitani" not in pr["name"]
    w = json.load(open(_R / "wang2015_atlas_provenance.json"))
    assert w["use_complete_atlas"] is True and w["no_performance_subselection"] is True
    assert _decision()["no_roi_selected_by_performance"] is True


def test_benson_secondary_only():
    sec = _seal()["frozen"]["secondary_rois"]["BENSON_V1V2V3"]
    assert sec["role"].startswith("SECONDARY")
    assert "cannot rescue" in sec["role"].lower()
    assert "cannot change primary" in sec["role"].lower()
    b = json.load(open(_R / "secondary_benson_results.json"))
    assert b["role"] == "SECONDARY" and b["cannot_change_primary_decision"] is True
    assert _seal()["frozen"]["subject_primary_pass_requires_all"]  # primary rule exists independently
    assert json.load(open(_R / "benson14_atlas_provenance.json"))["cannot_rescue_primary"] is True


def test_mni_target_space_pinned():
    pp = json.load(open(_R / "preprocessing_provenance.json"))
    assert pp["output_space"] == "MNI152NLin2009cAsym" and pp["resolution_mm"] == 2
    assert _seal()["frozen"]["output_space"] == "MNI152NLin2009cAsym 2mm isotropic"


def test_atlas_hashes_pinned_not_fabricated():
    w = json.load(open(_R / "wang2015_atlas_provenance.json"))
    assert w["version_pinned"] is True and w["outcome_independent"] is True
    # hash fields exist and are honestly null (verified at download), never fabricated
    assert w["pinned"]["sha256"] is None and w["pinned"]["md5"] is None
    b = json.load(open(_R / "benson14_atlas_provenance.json"))
    assert b["version_pinned"] is True and b["pinned"]["template_hashes"] is None


def test_no_smoothing_unless_sealed():
    pp = json.load(open(_R / "preprocessing_provenance.json"))
    assert pp["smoothing"] == "NONE" and pp["no_smoothing_unless_sealed"] is True
    assert _seal()["frozen"]["preprocessing"]["smoothing"] == "NONE (primary multivoxel reliability)"


def test_model_a_unchanged():
    glm = _seal()["frozen"]["GLM"]
    assert glm["model"].startswith("MODEL_A_LSA")
    assert glm["no_model_reopening"] is True and glm["no_lss_switch_on_results"] is True
    assert "cue" in glm["definition"] and "imagery" in glm["definition"] \
        and "post-video" in glm["definition"] and "nuisance" in glm["definition"]


def test_trial_contract_72_360_5():
    tc = _seal()["frozen"]["trial_contract"]["imagery"]
    assert tc["videos"] == 72 and tc["reps_per_video"] == 5
    assert tc["trials"] == 360 and tc["imagery_sessions"] == 5
    dc = json.load(open(_R / "dataset_contract.json"))
    assert dc["imagery_contract"]["videos"] == 72
    assert dc["imagery_contract"]["trials"] == 360
    assert dc["imagery_contract"]["imagery_sessions"] == 5
    assert dc["video_identity_correspondence_required"] == "72/72"
    assert dc["fail_closed_on_violation"] is True
    assert "trainPerception" in dc["exclude"]
    assert dc["trainPerception_parameter_tuning_forbidden"] is True


def test_reliability_estimator_session_disjoint_frozen():
    est = _seal()["frozen"]["reliability_estimator"]
    assert est["callable"] == "c3xb_reliability.reliability_with_inference_pairs"
    assert est["independent_unit"] == "imagery SESSION"
    assert "Spearman-Brown" in est["statistic"] and "session-disjoint" in est["statistic"]
    # the sealed estimator is the frozen C3XB callable, wired to the session-as-unit split
    from app.research.fmri.c3xb_reliability import reliability_with_inference_pairs
    rng = np.random.default_rng(0)
    n_sess, n_vid, reps, vox = 4, 6, 3, 8
    templates = rng.normal(size=(n_vid, vox))
    X, content, sess = [], [], []
    for s in range(n_sess):
        for v in range(n_vid):
            for _ in range(reps):
                X.append(templates[v] + 0.3 * rng.normal(size=vox))
                content.append(v)
                sess.append(s)  # independent unit = imagery session
    out = reliability_with_inference_pairs(np.array(X), np.array(content), np.array(sess),
                                           seed=20260909, n_perm=20, n_boot=20)
    # frozen schema: point estimate + within-unit permutation null + non-straddling bootstrap CI
    for k in ("reliability", "perm_p_one_sided", "bootstrap_ci95", "split_seed_values", "unit"):
        assert k in out
    assert out["unit"] == "run_pair_disjoint"  # the run-pair/session-disjoint unit machinery
    assert len(out["split_seed_values"]) == 3   # split-seed robustness triple


def test_null_bootstrap_seeds_sealed():
    seal = _seal()["frozen"]
    assert seal["null"]["scheme"] == "within-imagery-session video-label permutation"
    assert seal["null"]["no_cross_session_label_exchange"] is True
    assert seal["bootstrap"]["scheme"] == "non-straddling hierarchical bootstrap"
    assert "no imagery session/trial in both halves" in seal["bootstrap"]["constraint"]
    assert seal["split_seeds"]["base"] == 20260909
    assert seal["split_seeds"]["offsets"] == [0, 100, 200]
    assert seal["split_seeds"]["no_seed_selection"] is True


def test_cuevideo_falsification_required():
    seal = _seal()["frozen"]["cue_video_falsification"]
    assert seal["mandatory"] is True
    assert "Delta_I" in seal
    fals = json.load(open(_R / "cuevideo_falsification.json"))
    assert fals["mandatory"] is True
    # raw R_I alone is explicitly insufficient
    assert "not sufficient" in fals["criterion"].lower() or "NOT sufficient" in fals["criterion"]
    assert "cue/video contamination criterion PASS" in _seal()["frozen"]["subject_primary_pass_requires_all"]


def test_secondary_cannot_rescue_primary():
    d = _decision()
    assert d["secondary_roi_cannot_rescue_primary"] is True


def test_no_semantic_features_no_geometry_no_reconstruction():
    seal = _seal()
    for feat in seal["forbidden_features"]:
        assert isinstance(feat, str)
    for tok in ("CLIP", "DINO", "TimeSformer", "DeBERTa", "Stable Diffusion"):
        assert tok in seal["forbidden_features"]
    for g in ("CKA", "subspace overlap", "state transport"):
        assert g in seal["forbidden_geometry"]
    d = _decision()
    assert d["no_semantic_features"] and d["no_geometry"] and d["no_reconstruction"]
    # the assembler must IMPORT no geometry/semantic/reconstruction/neuroimaging module (the forbidden
    # names may legitimately appear inside the sealed declarative forbidden-lists, so scan imports only)
    src = (_ROOT / "backend/app/research/fmri/run_c3xat_seal_certify.py").read_text()
    imports = "\n".join(ln for ln in src.splitlines()
                        if ln.strip().startswith(("import ", "from "))).lower()
    for bad in ("c3g_geometry", "participation_ratio", "subspace_overlap", "linear_cka", "procrustes",
                "state_transport", "deberta", "timesformer", "stable_diffusion", "reconstruct",
                "nibabel", "nilearn", "clip", "dino", "torch", "transformers"):
        assert bad not in imports, bad


def test_dataset_rule_2of6_sealed():
    rule = _seal()["frozen"]["dataset_decision_rule"]
    assert rule[">=2/6 primary PASS"] == "C3XAT_D2_ATLAS_IMAGERY_QUALIFIED"
    assert rule["exactly 1/6"] == "C3XAT_D2_ATLAS_IMAGERY_LIMITED"
    assert rule["0/6 with valid measurement"] == "C3XAT_D2_ATLAS_IMAGERY_FAIL"
    assert rule["execution/provenance incomplete"] == "C3XAT_BLOCKED_*"
    assert rule["independent_of_c3xdr"] is True


def test_blocked_closeout_fabricates_no_outcome():
    d = _decision()
    if d["decision"].startswith("C3XAT_BLOCKED"):
        assert d["is_blocked_not_fail"] is True
        assert d["dataset_gate_evaluated"] is False
        assert d["subjects_processed"] == 0 and d["downloaded_bytes"] == 0
        assert d["no_outcome_fabricated"] is True
        assert d["c3xag_authorized"] is False
        # every per-subject reliability / QC record must carry null outcomes while blocked
        for s in _SUBS:
            rel = json.load(open(_R / f"reliability_{s}.json"))
            assert rel["status"] == "EXECUTION_BLOCKED"
            for k in ("reliability", "perm_p_one_sided", "bootstrap_ci95", "split_seed_values"):
                assert rel[k] is None, (s, k)
            qc = json.load(open(_R / f"roi_qc_{s}.json"))
            assert qc["wang25_voxel_count"] is None and qc["mask_sha256"] is None


def test_c3xag_authorized_only_if_qualified():
    d = _decision()
    if d["c3xag_authorized"] is True:
        assert d["decision"] == "C3XAT_D2_ATLAS_IMAGERY_QUALIFIED"
    for bad in ("C3XE", "C3XR", "C3XR-CAT", "C3XDR-R2", "geometry", "decoding", "reconstruction", "C4"):
        assert bad in d["does_NOT_authorize"]
