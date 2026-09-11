"""C3XAT-R1 — execution attempt 2 of the sealed C3XAT experiment on OrchestrAI.

This REUSES the C3XAT protocol seal (self_hash bb0d07ac...) WITHOUT MODIFICATION. It designs no new
protocol and changes nothing frozen (dataset, subjects, ROIs, Model A, estimator, permutation,
bootstrap, seeds, cue/video falsification, dataset gate). It records the ACTUAL state of the live
execution on the OrchestrAI cluster (namespace runai-romania-dev, connected via the explicit user
kubeconfig -- not the default context).

Honest-state rules (identical ethos to every prior gate): NO neural outcome (R_I/R_P/Delta_I) is
fabricated. Records for stages that have not produced verified output carry null values and an explicit
status. Confirmatory reliability requires the long-running fMRIPrep(x6)+estimator jobs to complete on
the persistent cluster and be collected on a later resumption; until then the decision is
C3XAT_R1_BLOCKED_EXECUTION_INCOMPLETE (BLOCKED != FAIL). C3XAG is NOT authorized.

Every literal below is a value actually observed live this session (kubectl / registry / S3 / job logs).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

C3XAT_SEAL = "bb0d07acb9a2cf8d271d4697acc6cde352b9b12cd38504203b14f8cf6079cee2"
C3XAT_R1_PARENT = "4caeb73"  # dependency-hardening tip
SUBS = ["S1", "S2", "S3", "S4", "S5", "S6"]
FMRIPREP_IMAGE = "nipreps/fmriprep:24.1.1"
FMRIPREP_DIGEST = "sha256:9aec0b83b3728795fa5a593d373c9bc5d4a7034e943a793173408e3b70e702c6"


def _sh(o):
    o = dict(o)
    o.pop("self_hash", None)
    o["self_hash"] = hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
    return o


def _dump(obj, path: Path):
    json.dump(_sh(obj), open(path, "w"), indent=2)


def build(out: Path, reports: Path) -> str:
    out.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    # ---- execution-attempt seal (references the UNCHANGED C3XAT seal) ---------------------------
    seal = {
        "artifact": "C3XAT_R1_EXECUTION_SEAL", "gate": "C3XAT_R1", "execution_attempt": 2,
        "reuses_c3xat_seal_unchanged": C3XAT_SEAL, "designs_new_protocol": False,
        "frozen_unchanged": ["dataset", "subjects", "primary_roi", "secondary_roi", "model_a",
                             "reliability_estimator", "permutation", "bootstrap", "seeds",
                             "cue_video_falsification", "dataset_gate"],
        "attempt1_decision_preserved": "C3XAT_BLOCKED_EXECUTION",
        "branch": "research/d2-atlas-raw-imagery-c3xat-r1", "parent_sha": C3XAT_R1_PARENT,
        "no_fabrication": True, "no_geometry": True, "no_decoding": True, "no_reconstruction": True,
        "no_semantic_features": True, "not_c3xag": True, "not_c4": True,
        "self_hash_field": "self_hash",
    }
    sealed = _sh(seal)
    json.dump(sealed, open(reports / "c3xat_r1_execution_seal.json", "w"), indent=2)
    seal_hash = sealed["self_hash"]

    # ---- cluster certification (LIVE, observed) -------------------------------------------------
    cluster = {
        "artifact": "C3XAT_R1_CLUSTER_CERTIFICATION", "seal_self_hash": seal_hash,
        "connected_via": "explicit user kubeconfig (~/Downloads/antoniu_iepure.yaml), NOT default context",
        "context": "antoniu-iepure@default", "namespace": "runai-romania-dev",
        "auth_can_i_get_pods": True, "auth_can_i_create_jobs": True, "auth_can_i_create_pvc": True,
        "auth_can_i_create_pods": True,
        "storage": {"default_storageclass": "nfs-client",
                    "provisioner": "nfs-subdir-external-provisioner (persistent NFS)",
                    "workspace_pvc": "c3xat-r1-workspace", "workspace_pvc_capacity": "600Gi",
                    "workspace_pvc_access_mode": "ReadWriteMany", "workspace_pvc_status": "Bound",
                    "workspace_pvc_volume": "pvc-5f104841-7e1d-40ec-a4ae-4df529ed0c7f"},
        "gpu": {"node": "k8s-worker-gpu-node-xe8545", "nvidia_gpu_capacity": 4,
                "additional_gpu_node": "k8s-worker-gpu-node-xe9680"},
        "egress": {"openneuro_s3": "HTTP 200 (ds005191/dataset_description.json)",
                   "templateflow_s3": "HTTP 200", "verified_from_pod": True, "verified_from_shell": True},
        "freesurfer_license": {"present": True, "in_cluster_secret": "c3xat-fs-license",
                               "committed_to_git": False},
        "status": "C3XAT_R1_REMOTE_INFRA_PASS",
        "advance_over_attempt1": "C3XAT_BLOCKED_EXECUTION (attempt 1) was due to the OrchestrAI kubeconfig "
                                 "being absent that session. Here the cluster is reachable, storage/GPU/"
                                 "egress/FreeSurfer-license are all certified live. That blocker is RESOLVED.",
    }
    _dump(cluster, out / "cluster_certification.json")

    # ---- container provenance (RESOLVED) --------------------------------------------------------
    container = {
        "artifact": "C3XAT_R1_CONTAINER_PROVENANCE", "seal_self_hash": seal_hash,
        "fmriprep_image": FMRIPREP_IMAGE, "fmriprep_digest": FMRIPREP_DIGEST,
        "digest_resolved_from": "Docker Hub registry (nipreps/fmriprep tag 24.1.1)",
        "freesurfer_bundled_in_fmriprep": True, "freesurfer_license_secret": "c3xat-fs-license",
        "output_space": "MNI152NLin2009cAsym", "resolution_mm": 2, "smoothing": "NONE",
        "status": "CONTAINER_PROVENANCE_RESOLVED",
        "note": "fMRIPrep 24.1.1 bundles FreeSurfer + ANTs + AFNI + TemplateFlow client; the exact "
                "component versions are captured from the pinned digest at run time.",
    }
    _dump(container, out / "container_provenance.json")

    # ---- atlas provenance (source identified; hashing runs in-pipeline) -------------------------
    atlas = {
        "artifact": "C3XAT_R1_ATLAS_PROVENANCE", "seal_self_hash": seal_hash,
        "primary_roi": "WANG25_TOPOGRAPHIC_VISUAL_NETWORK",
        "templateflow_hosts_wang2015": False, "templateflow_hosts_benson": False,
        "templateflow_query_result": "no atlas-Wang2015 / atlas-Benson objects under tpl-fsaverage or "
                                     "tpl-MNI152NLin2009cAsym (empty S3 listing)",
        "authoritative_source": "Wang et al. 2015 maximum-probability atlas via neuropythy (bundled, "
                                "fixed-hash fetch); native source space is fsaverage/FSL-MNI152",
        "target_space": "MNI152NLin2009cAsym 2mm",
        "resampling": "official TemplateFlow MNI152NLin6Asym->MNI152NLin2009cAsym transform, label-safe "
                      "(GenericLabel/nearest) interpolation; NO custom registration",
        "benson_secondary": "Benson14 via neuropythy, anatomy-predicted V1+V2+V3 union",
        "wang25_sha256": None, "benson14_sha256": None, "transform_sha256": None,
        "status": "ATLAS_SOURCE_IDENTIFIED_HASH_PENDING_INPIPELINE_RESOLUTION",
        "note": "hashes are computed and frozen inside the pinned pipeline container on the cluster before "
                "any R_I; recorded null here (not fabricated).",
    }
    _dump(atlas, out / "atlas_provenance.json")

    # ---- dataset acquisition (LIVE, running) ----------------------------------------------------
    acq = {
        "artifact": "C3XAT_R1_DATASET_ACQUISITION", "seal_self_hash": seal_hash,
        "dataset": "OpenNeuro ds005191", "version": "1.0.2", "name": "Mind Captioning",
        "author": "Tomoyasu Horikawa", "license": "CC0",
        "subjects_present": ["sub-01", "sub-02", "sub-03", "sub-04", "sub-05", "sub-06"],
        "bids_layout": {"anat_session": "ses-anat",
                        "imagery_sessions": ["ses-testImagery0%d" % i for i in range(1, 6)],
                        "perception_sessions": ["ses-testPerception01", "ses-testPerception02"],
                        "excluded_train_sessions": ["ses-trainPerception%02d" % i for i in range(1, 11)]},
        "imagery_sessions_count": 5,
        "selective_sync": "aws s3 sync s3://openneuro.org/ds005191 (exclude *ses-trainPerception*, "
                          "derivatives/*) -> PVC c3xat-r1-workspace:/work/ds005191",
        "trainPerception_excluded_from_analysis_and_tuning": True,
        "acquire_job": "c3xat-r1-acquire", "job_status_observed": "Running",
        "progress_observed": "~1.5 GiB / ~10 GiB at ~74 MiB/s (per-subject partial; full 6-subject sync "
                             "continues on the persistent PVC)",
        "input_hashing": "SHA-256 manifest of all *.nii.gz/*.tsv/*.json built by the acquire job on the PVC",
        "status": "ACQUISITION_IN_PROGRESS",
    }
    _dump(acq, out / "dataset_acquisition.json")

    # ---- per-subject reliability (execution incomplete; NOT fabricated) -------------------------
    for s in SUBS:
        rel = {"artifact": "C3XAT_R1_RELIABILITY", "subject": s, "seal_self_hash": seal_hash,
               "roi": "WANG25_TOPOGRAPHIC_VISUAL_NETWORK", "independent_unit": "imagery SESSION",
               "estimator": "c3xb_reliability.reliability_with_inference_pairs",
               "split_seeds": [20260909, 20261009, 20261109], "n_perm": 1000, "n_boot": 1000,
               "n_rep_point": 200, "status": "EXECUTION_INCOMPLETE",
               "R_I": None, "perm_p_one_sided": None, "bootstrap_ci95": None, "split_seed_min": None,
               "R_P": None, "cue_gain": None, "video_gain": None, "R_I_cuevideo_predicted": None,
               "Delta_I": None, "delta_inference": None, "subject_pass_status": None,
               "note": "requires completed fMRIPrep + atlas ROI + sealed estimator on the cluster; not yet "
                       "available this session. No value fabricated."}
        _dump(rel, out / f"reliability_{s}.json")

    # ---- decision -------------------------------------------------------------------------------
    decision = {
        "artifact": "C3XAT_R1_DECISION", "gate": "C3XAT_R1", "execution_attempt": 2,
        "seal_self_hash": seal_hash, "reuses_c3xat_seal": C3XAT_SEAL,
        "decision": "C3XAT_R1_BLOCKED_EXECUTION_INCOMPLETE", "is_blocked_not_fail": True,
        "infrastructure_gate": "C3XAT_R1_REMOTE_INFRA_PASS",
        "resolved_this_session": ["live OrchestrAI connection (explicit kubeconfig, ns runai-romania-dev)",
                                  "persistent storage (600Gi RWX nfs-client PVC, Bound)",
                                  "GPU capacity (4x A100 node)", "cluster+shell egress to OpenNeuro/TemplateFlow",
                                  "FreeSurfer license (in-cluster secret)",
                                  "fMRIPrep container digest (24.1.1 @ sha256:9aec0b83...)",
                                  "ds005191 BIDS contract verified (6 subj, 5 imagery sessions, "
                                  "trainPerception excludable)",
                                  "selective ds005191 acquisition launched and running"],
        "not_yet_complete": ["full ds005191 sync", "in-pipeline atlas hash resolution",
                             "fMRIPrep preprocessing of S1-S6", "S1 technical qualification",
                             "confirmatory R_I/R_P", "cue/video falsification", "dataset decision"],
        "why_not_fail": "no genuine fail-closed blocker was hit (cluster/storage/egress/license/container "
                        "all available). Only long-running preprocessing remains, which per protocol runs on "
                        "the persistent cluster and resumes; incomplete confirmatory measurement is BLOCKED, "
                        "not FAIL.",
        "resume_path": "on next resumption: collect the acquire job, run in-pipeline atlas resolution+hash, "
                       "launch fMRIPrep (digest-pinned, +FS license secret, MNI152NLin2009cAsym 2mm, no "
                       "smoothing), do S1 technical qualification (no R_I inspection), freeze impl hashes, "
                       "then execute the sealed session-disjoint reliability + cue/video falsification and "
                       "apply the frozen dataset gate.",
        "subjects_with_confirmatory_R_I": 0, "dataset_gate_evaluated": False,
        "no_neural_outcome_fabricated": True, "no_roi_selected_by_performance": True,
        "no_geometry": True, "no_decoding": True, "no_reconstruction": True, "no_semantic_features": True,
        "c3xag_authorized": False,
        "c3xag_authorization_condition": "ONLY C3XAT_D2_ATLAS_IMAGERY_QUALIFIED authorizes PREPARING C3XAG.",
        "does_NOT_authorize": ["C3XAG execution", "C3XE", "C3XR", "C4", "geometry", "decoding",
                               "reconstruction"],
        "immutable_prior_gates": ["C3XC", "C3XD", "C3XDR", "C3XDR-R1", "C3XPR", "C3XPA", "C3XAT"],
        "credentials_committed": False,
    }
    _dump(decision, out / "C3XAT_R1_DECISION.json")
    return decision["decision"]


def main() -> None:
    out = Path(os.environ.get("C3XAT_R1_OUT_DIR", "results/c3xat_r1"))
    reports = Path(os.environ.get("C3XAT_R1_REPORTS_DIR", "reports/c3xat_r1"))
    dec = build(out, reports)
    print("DECISION:", dec, "| C3XAG authorized: False | no neural outcome fabricated: True")


if __name__ == "__main__":
    main()
