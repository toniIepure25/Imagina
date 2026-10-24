"""ANIMUS-P2-XR adapter + method-inheritance tests (hermetic; no external datasets).

Verifies the BOLD5000 / THINGS-fMRI I/O adapters normalize each dataset's real event-table format into the
frozen P2 (onset, duration, stimulus_id) contract WITHOUT altering the GLM, and that catch/invalid rows are
handled correctly. Event samples below are verbatim headers + rows from the real OpenNeuro datasets
(ds001499 v1.3.1, ds004192 v1.0.7) captured during the prospective audit.
"""
from __future__ import annotations

from app.research.animus_p2xr.adapters import (
    ADAPTERS,
    BOLD5000Adapter,
    THINGSfMRIAdapter,
)

# --- real event samples (verbatim from the audit) ------------------------------------------------------
BOLD5000_EVENTS = (
    "onset\tduration\tSubj\tSess\tRun\tTrial\tImgName\tImgType\tStimOn(s)\tStimOff(s)\tResponse\tRT\tstim_file\n"
    "6.0367\t0.9678\t1\t1\t1\t1\tn01930112_19568.JPEG\timagenet\t6.0367\t7.0045\t2\t3.6309\tn01930112_19568.JPEG\n"
    "36.0121\t0.9844\t1\t1\t1\t4\tCOCO_train2014_000000420713.jpg\tcoco\t36.0121\t36.9965\t1\t2.47\tCOCO_train2014_000000420713.jpg\n"
    "46.0038\t1.0008\t1\t1\t1\t5\tsun_aabmvpxxlnnmodri.jpg\tscene\t46.0038\t47.0046\t1\t2.8\tsun_aabmvpxxlnnmodri.jpg\n"
)

THINGS_EVENTS = (
    "onset\tduration\ttrial_type\tcategory_nr\texemplar_nr\ttest_image_nr\tthings_category_nr\tthings_exemplar_nr\tresponse_time\tfile_path\n"
    "3.0\t0.5\texp\t205\t12\tn/a\t496.0\t12.0\tn/a\tdog/dog_12s.jpg\n"
    "12.0\t0.5\tcatch\t721\t8\tn/a\tn/a\tn/a\t0.871\tcatch008.jpg\n"
    "21.0\t0.5\ttest\t110\t13\t22.0\t253.0\t14.0\tn/a\tcandelabra/candelabra_14s.jpg\n"
)


def test_registry_maps_dataset_ids():
    assert ADAPTERS["ds001499"] is BOLD5000Adapter
    assert ADAPTERS["ds004192"] is THINGSfMRIAdapter


def test_bold5000_parses_all_visual_families():
    trials = BOLD5000Adapter().parse_events_text(BOLD5000_EVENTS)
    assert len(trials) == 3
    ids = [t.stimulus_id for t in trials]
    assert "n01930112_19568.JPEG" in ids
    assert "COCO_train2014_000000420713.jpg" in ids
    assert "sun_aabmvpxxlnnmodri.jpg" in ids
    # onsets/durations preserved as floats; identity == stim_file
    t0 = trials[0]
    assert abs(t0.onset - 6.0367) < 1e-6 and abs(t0.duration - 0.9678) < 1e-6
    assert t0.kind == "imagenet"


def test_bold5000_image_relpath_by_family():
    a = BOLD5000Adapter()
    assert a.image_relpath("n01930112_19568.JPEG") == "imagenet/n01930112_19568.JPEG"
    assert a.image_relpath("COCO_train2014_000000420713.jpg") == "coco/COCO_train2014_000000420713.jpg"
    assert a.image_relpath("sun_aabmvpxxlnnmodri.jpg") == "scene/sun_aabmvpxxlnnmodri.jpg"


def test_things_keeps_exp_and_test_excludes_catch():
    trials = THINGSfMRIAdapter().parse_events_text(THINGS_EVENTS)
    kinds = sorted(t.kind for t in trials)
    assert kinds == ["exp", "test"]  # catch excluded
    ids = [t.stimulus_id for t in trials]
    assert "dog/dog_12s.jpg" in ids and "candelabra/candelabra_14s.jpg" in ids
    assert all("catch" not in i for i in ids)


def test_things_identity_and_image_relpath():
    a = THINGSfMRIAdapter()
    assert a.image_relpath("dog/dog_12s.jpg") == "dog/dog_12s.jpg"
    trials = a.parse_events_text(THINGS_EVENTS)
    assert abs(trials[0].onset - 3.0) < 1e-9 and abs(trials[0].duration - 0.5) < 1e-9


def test_adapters_do_not_expose_glm_or_roi_hooks():
    # The adapters must only translate I/O; they must not carry ROI/HRF/decoder/metric knobs.
    for cls in (BOLD5000Adapter, THINGSfMRIAdapter):
        attrs = set(dir(cls))
        forbidden = {"hrf", "roi", "mask", "alpha", "decoder", "nuisance", "content_margin", "two_afc"}
        assert not (attrs & forbidden), f"{cls.__name__} leaks method internals: {attrs & forbidden}"


def test_invalid_rows_skipped():
    bad = (
        "onset\tduration\ttrial_type\tfile_path\n"
        "n/a\t0.5\texp\tx/x.jpg\n"          # missing onset
        "3.0\t\texp\ty/y.jpg\n"              # missing duration
        "5.0\t0.5\texp\t\n"                  # missing identity
    )
    assert THINGSfMRIAdapter().parse_events_text(bad) == []


# --- cross-dataset decision logic (frozen before outcomes) ---------------------------------------------
from app.research.animus_p2xr.decision import (  # noqa: E402
    FAIL,
    LIMITED,
    PASS,
    cross_dataset_decision,
    dataset_status,
)


def _pass_subject():
    return {"data_contract_pass": True, "atlas_qc_pass": True, "margin_M": 0.1,
            "permutation_p": 0.001, "bootstrap_ci_lower": 0.05, "all_seeds_positive": True}


def _null_subject():
    # at chance: fails margin / permutation / bootstrap gates (Type-I guard)
    return {"data_contract_pass": True, "atlas_qc_pass": True, "margin_M": 0.0004,
            "permutation_p": 0.42, "bootstrap_ci_lower": -0.002, "all_seeds_positive": False}


def test_required_passes_matches_inherited_rule():
    from app.core.animus.p2.gate import required_passes
    assert required_passes(4) == 2  # BOLD5000 N=4 -> 2
    assert required_passes(3) == 2  # THINGS   N=3 -> 2


def test_dataset_status_validated_limited_fail_blocked():
    # BOLD5000-like N=4, all valid
    v = dataset_status([_pass_subject(), _pass_subject(), _null_subject(), _null_subject()], n_eligible=4)
    assert v["status"] == "VALIDATED" and v["n_pass"] == 2 and v["required_passes"] == 2
    lim = dataset_status([_pass_subject(), _null_subject(), _null_subject(), _null_subject()], n_eligible=4)
    assert lim["status"] == "LIMITED" and lim["n_pass"] == 1
    fail = dataset_status([_null_subject()] * 4, n_eligible=4)
    assert fail["status"] == "FAIL" and fail["n_pass"] == 0
    # incomplete measurement -> BLOCKED (n_valid < n_eligible)
    blk = dataset_status([_pass_subject(), _pass_subject()], n_eligible=4)
    assert blk["status"] == "BLOCKED"


def test_cross_dataset_rule():
    V = {"status": "VALIDATED"}
    L = {"status": "LIMITED"}
    F = {"status": "FAIL"}
    assert cross_dataset_decision({"ds001499": V, "ds004192": V}) == PASS
    assert cross_dataset_decision({"ds001499": V, "ds004192": F}) == LIMITED
    assert cross_dataset_decision({"ds001499": V, "ds004192": L}) == LIMITED
    assert cross_dataset_decision({"ds001499": F, "ds004192": F}) == FAIL
    assert cross_dataset_decision({"ds001499": L, "ds004192": L}) == FAIL


def test_no_pooled_rescue():
    # Each dataset has 1 pass but requires 2 -> both LIMITED -> cross must be FAIL, never PASS.
    b = dataset_status([_pass_subject(), _null_subject(), _null_subject(), _null_subject()], 4)
    t = dataset_status([_pass_subject(), _null_subject(), _null_subject()], 3)
    assert b["status"] == "LIMITED" and t["status"] == "LIMITED"
    assert cross_dataset_decision({"ds001499": b, "ds004192": t}) == FAIL


def test_type_i_null_datasets_fail():
    # Pure-null cohorts must not validate (guards the gate against false positives).
    b = dataset_status([_null_subject()] * 4, 4)
    t = dataset_status([_null_subject()] * 3, 3)
    assert b["status"] == "FAIL" and t["status"] == "FAIL"
    assert cross_dataset_decision({"ds001499": b, "ds004192": t}) == FAIL


# --- protocol seal inheritance + firewall (pre-outcome) ------------------------------------------------
import json  # noqa: E402
import os  # noqa: E402

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_XR = os.path.join(_ROOT, "results", "animus_p2xr")


def _load(name):
    return json.load(open(os.path.join(_XR, name), encoding="utf-8"))


def test_seal_inherits_p2_method_exactly():
    seal = _load("animus_p2xr_protocol_seal.json")
    assert "DATASET I/O ADAPTERS" in seal["only_changes_vs_p2"]
    assert seal["roi"]["space"] == "MNI152NLin2009cAsym:res-2"
    assert seal["roi"]["wang25_sha256"] == "19b681ecba5c8d2aa323b8f6e15d36191d4036cea070d095663a790690c544fc"
    assert seal["smoothing"] == "NONE" and "@sha256:" in seal["fmriprep_digest"]
    enc = seal["target_encoder"]
    assert enc["model_id"] == "open_clip:ViT-B-32" and enc["pretrained"] == "laion2b_s34b_b79k"
    assert seal["permutation"]["n_perm"] == 1000 and seal["identity_bootstrap"]["n_boot"] == 1000
    assert seal["evaluation_seeds"] == [20260909, 20261009, 20261109]
    assert seal["cross_dataset_decision"]["no_pooled_rescue"] is True


def test_denominators_frozen_seven_total():
    d = _load("participant_denominator_freeze.json")
    assert d["frozen_before_outcomes"] and d["no_performance_based_selection"]
    assert d["total_denominator"] == 7
    assert d["datasets"]["ds001499"]["n_eligible"] == 4 and d["datasets"]["ds004192"]["n_eligible"] == 3


def test_seal_keeps_imagery_unauthorized_and_nod_closed():
    seal = _load("animus_p2xr_protocol_seal.json")
    assert seal["imagery_dream_reconstruction"] == "UNAUTHORIZED"
    assert seal["c3xag_authorized"] is False and seal["p3_execution"] is False
    assert "CLOSED" in seal["nod_status"]


def test_p2xr_ci_guard_passes():
    from app.research.animus_p2xr.run_p2xr_ci_guard import main
    assert main() == 0
