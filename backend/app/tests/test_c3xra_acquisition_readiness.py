"""Hermetic C3XRA acquisition-readiness tests (design-only; NO human/neural data).

Fast, deterministic checks of the frozen acquisition package: schedule identity/run contracts and
deterministic replay, timing-design rank/collinearity, hardware-free task dry-run counts, mock-BIDS
structural validity, seal self-hashes, anchor immutability wiring, and the contamination-operator
invariants (perfect leakage => Delta exactly 0; contamination channel carries ~no imagery). The heavy
full synthetic E2E replay (1000-resample) runs as a separate CI step, not here.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import tempfile

import numpy as np
import pytest

from app.research.fmri import c3xra_analysis as A
from app.research.fmri import c3xra_bids as B
from app.research.fmri import c3xra_schedule as S
from app.research.fmri import c3xra_task as T

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RESULTS = os.path.join(ROOT, "results", "c3xra")
CHOSEN_UNITS = 7


def _load(name):
    with open(os.path.join(RESULTS, name), encoding="utf-8") as f:
        return json.load(f)


def _recompute_self_hash(obj):
    o = dict(obj)
    o.pop("self_hash", None)
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


# ---- schedule ----------------------------------------------------------------
@pytest.mark.parametrize("nu", [5, 7, 9])
def test_imagery_contract_all_ids_once_per_unit(nu):
    for p in range(1, 6):
        r = S.verify_imagery_contract(p, nu)
        assert r["contract_pass"]
        assert r["n_total_trials"] == nu * S.N_IDENTITIES


@pytest.mark.parametrize("nu", [5, 7, 9])
def test_perception_units_complete_and_disjoint(nu):
    for p in range(1, 6):
        assert S.verify_perception_contract(p, nu)["contract_pass"]


def test_imagery_run_membership_balanced_complete():
    for p in range(1, 4):
        rows = S.imagery_trials(p, CHOSEN_UNITS)
        for u in range(1, CHOSEN_UNITS + 1):
            runs = {}
            for r in [x for x in rows if x["imagery_unit"] == u]:
                runs.setdefault(r["run"], []).append(r["video_id"])
            assert len(runs) == S.IMAGERY_RUNS_PER_UNIT
            assert all(len(v) == S.IMAGERY_TRIALS_PER_RUN for v in runs.values())
            assert sorted(v for vs in runs.values() for v in vs) == list(range(1, 73))


def test_schedule_deterministic_and_participant_distinct():
    assert S.imagery_trials(1, CHOSEN_UNITS) == S.imagery_trials(1, CHOSEN_UNITS)
    assert S.imagery_schedule(1, CHOSEN_UNITS) != S.imagery_schedule(2, CHOSEN_UNITS)


def test_no_systematic_within_run_adjacency():
    for p in range(1, 4):
        assert S.adjacency_confound(p, CHOSEN_UNITS)["no_systematic_adjacency"]


def test_schedule_contract_artifact_matches_engine():
    c = _load("schedule_contract.json")
    assert c["contract_pass"] and c["imagery_units"] == CHOSEN_UNITS
    assert c["imagery_runs_per_unit"] == S.IMAGERY_RUNS_PER_UNIT


# ---- timing design -----------------------------------------------------------
def test_timing_audit_rank_and_collinearity():
    a = _load("timing_design_audit.json")
    assert a["rank_deficiency"] == 0
    assert a["condition_number"] <= a["predeclared_bounds"]["condition_number_max"]
    assert a["max_vif"] <= a["predeclared_bounds"]["vif_max"]
    assert a["audit_pass"]


# ---- task dry-run ------------------------------------------------------------
def test_task_dryrun_mock_contract():
    tmp = tempfile.mkdtemp()
    log = T.CrashSafeLog(os.path.join(tmp, "r.jsonl"))
    log.open()
    rows = T.run_imagery_run(1, 1, 1, T.MockBackend(seed=111), log)
    log.close()
    assert len(rows) == S.IMAGERY_TRIALS_PER_RUN
    for r in rows:
        assert r["events_present"] == ["cue", "imagery", "postvideo", "eval"]
        assert r["cue_onset"] < r["imagery_onset"] < r["postvideo_onset"] < r["eval_onset"]
    ids = [r["video_id"] for r in rows]
    assert len(ids) == len(set(ids))  # no duplicate identity in a run


def test_task_dryrun_validation_artifact_pass():
    assert _load("task_dryrun_validation.json")["pass"]


# ---- BIDS --------------------------------------------------------------------
def test_mock_bids_structurally_valid():
    pytest.importorskip("nibabel")  # writing the synthetic mock needs nibabel (neural extra)
    root = tempfile.mkdtemp(prefix="c3xra_bids_test_")
    B.generate(root, imagery_units=1, imagery_runs=1, perception_units=1)
    assert os.path.exists(os.path.join(root, "dataset_description.json"))
    bolds = glob.glob(os.path.join(root, "**", "*_bold.nii.gz"), recursive=True)
    assert bolds
    for b in bolds:
        assert os.path.exists(b.replace("_bold.nii.gz", "_events.tsv"))


def test_bids_dryrun_artifact_zero_errors():
    v = _load("bids_dryrun_validation.json")
    assert v["structural_error_count"] == 0 and v["pass"]


# ---- contamination-operator invariants (fast; no heavy inference) -----------
def test_perfect_leakage_gives_zero_delta_exactly():
    """obs == contamination prediction => Delta = R_I(obs) - R_I(pred) is exactly 0 => never a valid PASS."""
    from app.research.fmri import c3xat_pipeline as P
    tup = A.simulate_scenario("adv_perfect_cue_leakage", n_units=5, n_id=12, vox=30)
    obs, pred, content, unit = tup[0], tup[1], tup[2], tup[3]
    assert np.allclose(obs, pred)
    sens = P.paired_delta_sensitivity(obs, pred, content, unit, n_boot=20)
    assert sens["delta_point"] == 0.0
    assert not sens["criterion_pass"]


def test_contamination_channel_has_near_zero_imagery():
    tup = A.simulate_scenario("imagery_plus_contam", n_units=5, n_id=12, vox=40)
    assert tup[-1]["pred_has_zero_imagery"] < 0.25  # small-sample tolerance


def test_cohort_gate_logic():
    assert A.cohort_decision(3, 9, 9) == "C3XRP_REPLICATION_QUALIFIED"
    assert A.cohort_decision(1, 9, 9) == "C3XRP_REPLICATION_LIMITED"
    assert A.cohort_decision(0, 9, 9) == "C3XRP_REPLICATION_FAIL"
    assert A.cohort_decision(3, 8, 9) == "C3XRP_BLOCKED_INCOMPLETE_MEASUREMENT"


# ---- seals & anchor ----------------------------------------------------------
SEALS = ["c3xra_anchor.json", "participant_plan.json", "final_measurement_schedule_decision.json",
         "schedule_contract.json", "stimulus_provenance.json", "timing_design_audit.json",
         "mri_sequence_contract.json", "task_dryrun_validation.json", "bids_dryrun_validation.json",
         "acquisition_qc_seal.json", "preprocessing_execution_seal.json", "behavior_secondary_seal.json",
         "spatial_specificity_freeze.json", "acquisition_resource_model.json",
         "synthetic_e2e_replay.json"]


@pytest.mark.parametrize("name", SEALS)
def test_seal_self_hash_valid(name):
    obj = _load(name)
    assert "self_hash" in obj
    assert obj["self_hash"] == _recompute_self_hash(obj)


def test_anchor_records_immutable_prior_decisions():
    a = _load("c3xra_anchor.json")
    assert a["c3xat_r1"]["decision"] == "C3XAT_D2_ATLAS_IMAGERY_LIMITED"
    assert a["c3xat_r1"]["pass"] == "1/6" and a["c3xat_r1"]["may_change"] is False
    assert a["c3xrp"]["may_change"] is False
    assert a["c3xag_authorized"] is False
    assert len(a["immutable_referenced_artifacts"]) >= 11


def test_qc_seal_excludes_reliability_from_technical_validity():
    q = _load("acquisition_qc_seal.json")
    assert q["neural_reliability_excluded_from_technical_validity"] is True
    assert q["reliability_never_determines_valid_run_session_or_participant"] is True


def test_participant_plan_forbids_reliability_exclusions():
    p = _load("participant_plan.json")
    forb = " ".join(p["forbidden_exclusions"]).lower()
    assert "r_i" in forb and "vividness" in forb and "non-responder" in forb
    assert p["vividness_not_inclusion_criterion"] is True
    assert p["no_responder_enrichment"] is True
