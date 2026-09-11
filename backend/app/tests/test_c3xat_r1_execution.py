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
