"""C3XDR-R1 execution-attempt-2 invariants (hermetic; NO cluster/network/BOLD). Guards the explicit
remote audit, credential safety (no kubeconfig/secrets in git), persistent-storage gate, unchanged
scientific seal (Model A / estimator / ROI / threshold), ROI-provenance fail-closed, and BLOCKED!=FAIL.
"""
import hashlib
import json
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_R1 = _ROOT / "results" / "c3xdr_r1"
_SEAL_HASH = "7afc79466c75b671865fc787a56e8e421b4774bfd3d2b65b133092450302f43d"
_HASHED = [
    "results/c3xdr_r1/remote_cluster_audit.json",
    "results/c3xdr_r1/storage_certification.json",
    "results/c3xdr_r1/container_execution_certification.json",
    "results/c3xdr_r1/c3xdr_r1_environment_manifest.json",
    "results/c3xdr_r1/c3xdr_r1_execution_attempt.json",
    "results/c3xdr_r1/raw_acquisition_manifest_preflight.json",
    "results/c3xdr_r1/roi_provenance.json",
    "results/c3xdr_r1/C3XDR_R1_DECISION.json",
] + [f"results/c3xdr_r1/reliability_S{i}.json" for i in range(1, 7)]


def _verify(o):
    o = dict(o)
    h = o.pop("self_hash")
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest() == h


def test_all_artifact_self_hashes():
    for rel in _HASHED:
        p = _ROOT / rel
        if not p.exists():
            continue
        o = json.load(open(p))
        if "self_hash" in o:
            assert _verify(o), rel


def test_execution_attempt_references_unchanged_seal():
    p = _R1 / "c3xdr_r1_execution_attempt.json"
    if not p.exists():
        return
    o = json.load(open(p))
    assert o["execution_attempt"] == 2
    assert o["scientific_seal"] == _SEAL_HASH
    for k in ("scientific_protocol_changed", "model_changed", "estimator_changed", "ROI_changed",
              "storage_requirement_changed"):
        assert o[k] is False
    # the referenced C3XDR seal itself still verifies (immutable) with the same hash
    s = json.load(open(_ROOT / "reports/c3xdr/c3xdr_execution_seal.json"))
    assert s["self_hash"] == _SEAL_HASH
    assert _verify(s)
    assert s["primary_estimator_frozen"]["model"] == "MODEL_A_LSA"


def test_no_credentials_or_kubeconfig_committed():
    tracked = subprocess.run(["git", "ls-files"], cwd=_ROOT, capture_output=True, text=True).stdout
    assert "antoniu_iepure" not in tracked
    for bad in (".kube/config", "id_ed25519", "kubeconfig"):
        assert bad not in tracked
    # no secret material inside any committed c3xdr_r1 artifact
    for p in _R1.glob("*.json"):
        blob = p.read_text()
        for bad in ("BEGIN PRIVATE KEY", "BEGIN RSA", "BEGIN OPENSSH", "client-key-data",
                    "client-certificate-data", "token:", "-----BEGIN"):
            assert bad not in blob, (p.name, bad)


def test_explicit_audit_not_default_localhost():
    p = _R1 / "remote_cluster_audit.json"
    if not p.exists():
        return
    o = json.load(open(p))
    assert "localhost" not in o["cluster_server"]
    assert o["cluster_server"].startswith("https://")
    assert o["kubeconfig"]["committed_to_git"] is False
    assert "EXPLICIT --kubeconfig" in o["note"]


def test_storage_gate_and_ephemeral_rejected():
    p = _R1 / "storage_certification.json"
    if not p.exists():
        return
    o = json.load(open(p))
    assert o["requirement_GB"] == 300
    if o["requirement_met"]:
        assert o["usable_persistent_free_GB"] >= 300
        assert o["status"] == "C3XDR_R1_REMOTE_INFRA_PASS"
        for v in o["persistent_volumes"]:
            assert v["storageclass"] in ("nfs-client", "local-path")
        assert any("tmpfs" in e or "emptyDir" in e or "node-local" in e for e in o["ephemeral_excluded"])


def test_container_image_has_digest():
    p = _R1 / "container_execution_certification.json"
    if not p.exists():
        return
    o = json.load(open(p))
    assert o["base_pod_image_digest"].startswith("sha256:")


def test_roi_provenance_failclosed():
    p = _R1 / "roi_provenance.json"
    if not p.exists():
        return
    o = json.load(open(p))
    assert o["status"] == "C3XDR_R1_BLOCKED_ROI_PROVENANCE"
    assert o["evidence"]["repo_defines_roi_from_raw"] is False
    assert o["not_resolved_by_infrastructure"] is True


def test_no_semantic_or_geometry_imports():
    src = (_ROOT / "backend/app/research/fmri/run_c3xdr_r1_decision.py").read_text()
    low = src.lower()
    for bad in ("deberta", "timesformer", "c3g_geometry", "participation_ratio", "subspace_overlap",
                "linear_cka", "procrustes", "crossnobis"):
        assert bad not in low, bad
    for bad in ("CLIP", "DINO"):
        assert bad not in src, bad


def test_decision_blocked_not_fail_and_authorizes_nothing():
    p = _R1 / "C3XDR_R1_DECISION.json"
    if not p.exists():
        return
    o = json.load(open(p))
    assert o["decision"].startswith("C3XDR_R1_BLOCKED") or o["decision"].startswith("C3XDR_R1_D2_")
    if o["decision"].startswith("C3XDR_R1_BLOCKED"):
        assert o["is_blocked_not_fail"] is True
        assert o["raw_reliability_gate_evaluated"] is False
        assert o["subjects_processed"] == 0 and o["downloaded_bytes"] == 0
        assert o["authorizes"] == "nothing (blocked); C3XE preparation NOT authorized"
        for x in ("C3XE", "state geometry", "C4"):
            assert x in o["does_NOT_authorize"]
    assert o["scientific_seal"] == _SEAL_HASH
    assert o["no_credentials_committed"] and o["no_raw_neural_data_committed"]
    # infra blocker resolved; ROI provenance is the isolated barrier
    assert o["infrastructure_gate"] == "C3XDR_R1_REMOTE_INFRA_PASS"


def test_trainperception_excluded_and_contracts_frozen():
    pf = _R1 / "raw_acquisition_manifest_preflight.json"
    if pf.exists():
        o = json.load(open(pf))
        assert "trainPerception" in o["planned_exclude"]
        assert "trainPerception" not in json.dumps(o["planned_include"])
        assert o["downloaded_bytes"] == 0
    s = json.load(open(_ROOT / "reports/c3xdr/c3xdr_execution_seal.json"))
    assert s["contracts"]["imagery"]["trials"] == 360
    assert s["contracts"]["imagery"]["videos"] == 72
    assert s["contracts"]["imagery"]["reps_per_video"] == 5
