"""C3XDR-R1 artifact assembler (execution attempt 2 of the sealed C3XDR question).

Records the explicit OrchestrAI remote-cluster audit (NO credentials/secrets), the persistent-
storage certification, container-execution certification, environment manifest, and the honest
Phase-1 determination: the remote infrastructure gate PASSES (cluster reachable, 107 TB persistent
NFS, Kubernetes container execution), but the released KamitaniLab localizer ROIs cannot be
reproducibly mapped into a raw-derived functional space from public artifacts (no preprocessing-from-
raw pipeline / ROI masks / raw->functional transform are published; getRoiVoxelIdx.m reads ROI
indices only from the released .mat). Per the sealed "do NOT approximate ROI mapping" rule this stops
BEFORE any raw download. Nothing fabricated; no secrets serialized.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

SEAL_HASH = "7afc79466c75b671865fc787a56e8e421b4774bfd3d2b65b133092450302f43d"


def _sh(o):
    o = dict(o)
    o.pop("self_hash", None)
    o["self_hash"] = hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
    return o


def main() -> None:
    out = Path(os.environ.get("C3XDR_R1_OUT_DIR", "results/c3xdr_r1"))
    out.mkdir(parents=True, exist_ok=True)

    cluster = {
        "artifact": "C3XDR_R1_REMOTE_CLUSTER_AUDIT", "status": "REACHABLE_AUTHENTICATED",
        "kubeconfig": {"found": True, "path": "C:/Users/ComputaCenter/Downloads/antoniu_iepure.yaml",
                       "size_bytes": 5626,
                       "sha256": "d9380cc31d714415c39831b706b19b18d2e878ee1df99a39ed8529d2aac9ba48",
                       "committed_to_git": False, "secrets_printed": False},
        "context": "antoniu-iepure@default", "namespace": "runai-romania-dev",
        "cluster_server": "https://10.130.123.31:10443", "tcp_reachable": True,
        "rbac": {"get_pods": True, "get_pvc": True, "create_pods": True, "create_jobs": True,
                 "delete_jobs": True, "get_pods_log": True, "create_pods_exec": True,
                 "create_pvc": True, "get_nodes": True, "get_storageclasses": True,
                 "kube_system_forbidden": True},
        "execution_pod": "orchestraiq-jupyter-5d6c688775-fbxj5 (Running 5d+, node k8s-worker-gpu-node-xe8545)",
        "note": "audited via EXPLICIT --kubeconfig (not default/localhost). No credentials serialized."}

    storage = {
        "artifact": "C3XDR_R1_STORAGE_CERTIFICATION", "status": "C3XDR_R1_REMOTE_INFRA_PASS",
        "requirement_GB": 300, "preferred_GB": 500, "requirement_met": True,
        "persistent_volumes": [
            {"pvc": "orchestraiq-jupyter-pvc", "capacity": "1Ti", "storageclass": "nfs-client",
             "access": "RWO", "mount": "/home/jovyan/legacy-work",
             "nfs_backend": "10.130.200.199:/ifs/bcm11/...-orchestraiq-jupyter-pvc-...",
             "fs": "nfs4", "size_T": 138, "avail_T": 107},
            {"pvc": "orchestraiq-jupyter-extra-pvc", "capacity": "1Ti", "storageclass": "nfs-client",
             "access": "RWO", "mount": "/home/jovyan/work",
             "nfs_backend": "10.130.200.199:/ifs/bcm11/...-orchestraiq-jupyter-extra-pvc-...",
             "fs": "nfs4", "size_T": 138, "avail_T": 107}],
        "usable_persistent_free_GB": 107000,
        "ephemeral_excluded": ["/home/jovyan/local-data (xfs node-local)", "dshm (tmpfs 8Gi)", "emptyDir local-storage"],  # noqa: E501
        "persistence_evidence": "Bound nfs-client (NFS subdir provisioner) PVCs, age 5d+; NFS network-backed "
                                "storage survives pod restart (PVC persistence contract). A write-probe was "
                                "intentionally NOT performed to avoid mutating the user's active jupyter "
                                "workspace (sealed: do not disturb production workloads).",
        "default_storageclass": "nfs-client (also local-path available); can create new >=300Gi PVC if needed"}

    container = {
        "artifact": "C3XDR_R1_CONTAINER_EXECUTION_CERTIFICATION", "status": "AVAILABLE",
        "mode": "Kubernetes Job with pinned image digest + persistent NFS PVC (no docker-in-docker required)",
        "base_pod_image": "quay.io/jupyter/pytorch-notebook:cuda12-latest",
        "base_pod_image_digest": "sha256:85ab930435b7afc06396e2949a4fe508d027a7980a319bec6a92f827578e5343",
        "compute": {"cpus": 256, "mem_Gi": 1007, "gpu": "NVIDIA A100-SXM4-40GB", "kernel": "6.8.0-51-generic",
                    "python": "3.13.15"},
        "preprocessing_stack_in_base_image": {"fmriprep": False, "fsl": False, "flirt": False,
                                              "recon-all": False, "spm12": False, "nibabel": False},
        "note": "K8s can run any pinned preprocessing container as a Job; container execution is NOT the "
                "blocker. The blocker is scientific ROI/preprocessing PROVENANCE (below), independent of "
                "which container is used."}

    env = {
        "artifact": "C3XDR_R1_ENVIRONMENT_MANIFEST", "status": "INFRA_AVAILABLE_PROVENANCE_BLOCKED",
        "cluster": cluster["cluster_server"], "namespace": cluster["namespace"],
        "execution_pod": cluster["execution_pod"], "image_digest": container["base_pod_image_digest"],
        "compute": container["compute"], "persistent_data_path": "/home/jovyan/work (nfs-client PVC, 107T free)",
        "preprocessing_environment_frozen": False,
        "reason_not_frozen": "no reproducible published preprocessing pipeline + no reproducible released-ROI "
                             "space to target (see roi_provenance)."}

    attempt = {
        "artifact": "C3XDR_R1_EXECUTION_ATTEMPT", "execution_attempt": 2,
        "scientific_seal": SEAL_HASH,
        "scientific_protocol_changed": False, "model_changed": False, "estimator_changed": False,
        "ROI_changed": False, "storage_requirement_changed": False,
        "note": "Retry solely to test the OrchestrAI kubeconfig that attempt-1's audit did not exercise. "
                "Same sealed C3XDR protocol/model/estimator/ROI/threshold."}

    preflight = {
        "artifact": "C3XDR_R1_RAW_ACQUISITION_MANIFEST_PREFLIGHT", "status": "NOT_ACQUIRED_BLOCKED",
        "dataset": "ds005191 v1.0.2", "planned_include": ["testImagery", "testPerception", "events", "sidecars",
                                                          "anat", "fmap if required"],
        "planned_exclude": ["trainPerception"], "subjects": ["S1", "S2", "S3", "S4", "S5", "S6"],
        "expected_bytes_GB": 139.4, "downloaded_bytes": 0,
        "reason": "Phase-1 gate (reproducible preprocessing + certified ROI mapping) failed BEFORE download "
                  "(protocol: determine the pipeline BEFORE acquiring raw BOLD)."}

    roi = {
        "artifact": "C3XDR_R1_ROI_PROVENANCE", "status": "C3XDR_R1_BLOCKED_ROI_PROVENANCE",
        "primary_roi": "VC", "secondary": ["V1", "LVC", "HVC"],
        "evidence": {
            "released_roi_source": "KamitaniLab preprocessed .mat metainf.roiname / roiind_value (localizer-"
                                   "defined voxel indices in the released preprocessed space)",
            "repo_defines_roi_from_raw": False,
            "getRoiVoxelIdx": "reads ROI indices ONLY from the released .mat (metainf); does not define/map from raw",
            "preprocessing_from_raw_code_published": False,
            "roi_masks_or_raw_to_functional_transform_published": False,
            "released_reference_EPI_for_registration_published": False,
            "figshare_contents": "block-averaged single-trial amplitude .mat + DNN features + results + videos "
                                 "(no timeseries, no ROI mask, no transform, no preprocessing code)"},
        "why_blocked": "Neither Phase-1 option is satisfiable from public artifacts: (1) the exact KamitaniLab "
                       "functional space cannot be reproduced (no published preprocessing pipeline/params); "
                       "(2) the released-ROI space cannot be targeted (undocumented, no reference volume); "
                       "(3) no independently certifiable raw->released ROI transform exists (the .mat gives "
                       "voxel indices/xyz in an undocumented per-subject space with no distributed reference). "
                       "Sealed rule forbids approximating VC.",
        "not_resolved_by_infrastructure": True}

    stubs = {
        "technical_qualification_S1.json": {"artifact": "C3XDR_R1_TECHNICAL_QUALIFICATION_S1",
            "status": "NOT_EXECUTED_BLOCKED", "reason": "blocked at Phase-1 ROI/preprocessing provenance before S1 processing"},  # noqa: E501
        "cue_magnitude.json": {"artifact": "C3XDR_R1_CUE_MAGNITUDE", "status": "NOT_MEASURED_BLOCKED",
            "reason": "requires raw VC betas; pipeline blocked at ROI provenance"},
        "cuevideo_falsification.json": {"artifact": "C3XDR_R1_CUEVIDEO_FALSIFICATION", "status": "NOT_EXECUTED_BLOCKED",
            "reason": "requires raw Model-A betas; blocked"},
        "temporal_controls.json": {"artifact": "C3XDR_R1_TEMPORAL_CONTROLS", "status": "NOT_EXECUTED_BLOCKED",
            "reason": "requires raw betas; blocked"},
    }
    for s in range(1, 7):
        stubs[f"reliability_S{s}.json"] = {"artifact": "C3XDR_R1_RELIABILITY", "subject": f"S{s}",
            "status": "NOT_PRODUCED_BLOCKED", "reason": "no raw betas (Phase-1 ROI/preprocessing provenance blocked)"}

    decision = {
        "artifact": "C3XDR_R1_DECISION", "gate": "C3XDR_R1", "execution_attempt": 2,
        "scientific_seal": SEAL_HASH,
        "decision": "C3XDR_R1_BLOCKED_ROI_PROVENANCE",
        "is_blocked_not_fail": True,
        "infrastructure_gate": "C3XDR_R1_REMOTE_INFRA_PASS",
        "storage_certified": True, "usable_persistent_free_GB": 107000,
        "container_execution_available": True,
        "advance_over_c3xdr": "C3XDR_BLOCKED_STORAGE is RESOLVED (remote cluster + 107 TB persistent NFS + "
                              "Kubernetes container execution confirmed via the OrchestrAI kubeconfig). The "
                              "true remaining blocker is isolated: ROI/preprocessing PROVENANCE.",
        "raw_reliability_gate_evaluated": False, "subjects_processed": 0, "downloaded_bytes": 0,
        "authorizes": "nothing (blocked); C3XE preparation NOT authorized",
        "does_NOT_authorize": ["C3XE", "C3XR", "C3XR-CAT", "reconstruction", "captioning",
                               "semantic decoding", "state geometry", "C4"],
        "c3xc_status": "PRESERVED, immutable", "c3xd_status": "PRESERVED, immutable",
        "c3xdr_status": "PRESERVED, immutable; C3XDR_BLOCKED_STORAGE was correct for attempt 1",
        "what_would_unblock": [
            "authoritative KamitaniLab preprocessing pipeline+parameters to reproduce the released functional "
            "space exactly (so the released localizer ROIs are directly reusable), OR",
            "released ROI masks / reference EPI / raw->functional transform enabling an independently certified "
            "ROI mapping (author request may be required)",
            "then replay the frozen C3XDR seal on the (now available) remote infrastructure"],
        "no_geometry_computed": True, "no_reconstruction": True, "not_c4": True,
        "no_raw_neural_data_committed": True, "no_credentials_committed": True, "no_large_download_attempted": True}

    json.dump(_sh(cluster), open(out / "remote_cluster_audit.json", "w"), indent=2)
    json.dump(_sh(storage), open(out / "storage_certification.json", "w"), indent=2)
    json.dump(_sh(container), open(out / "container_execution_certification.json", "w"), indent=2)
    json.dump(_sh(env), open(out / "c3xdr_r1_environment_manifest.json", "w"), indent=2)
    json.dump(_sh(attempt), open(out / "c3xdr_r1_execution_attempt.json", "w"), indent=2)
    json.dump(_sh(preflight), open(out / "raw_acquisition_manifest_preflight.json", "w"), indent=2)
    json.dump(_sh(roi), open(out / "roi_provenance.json", "w"), indent=2)
    for name, obj in stubs.items():
        json.dump(_sh(obj), open(out / name, "w"), indent=2)
    json.dump(_sh(decision), open(out / "C3XDR_R1_DECISION.json", "w"), indent=2)
    print("infra:", storage["status"], "| decision:", decision["decision"])


if __name__ == "__main__":
    main()
