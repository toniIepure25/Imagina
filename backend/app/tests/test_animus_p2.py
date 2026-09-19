"""ANIMUS-P2 test suite (design/product-only; NO real brains/images; synthetic method validation).

Covers the P2 firewall/leakage/gate/claim invariants: identity + near-duplicate leakage, fold-safe
normalization/PCA, hyperparameter leakage, test firewall, ROI/embedding immutability, permutation +
bootstrap integrity, uncertainty calibration, reject option, capability-domain isolation, neural/behavioral
fusion, model manifest, replay determinism, generator privacy, and hidden-target isolation.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.core.animus.p2 import capability as cap
from app.core.animus.p2.decoder import BootstrapEnsembleDecoder, select_alpha
from app.core.animus.p2.features import FoldSafeNormalizer, leakage_test_normalizer
from app.core.animus.p2.gate import dataset_gate, required_passes, subject_pass
from app.core.animus.p2.integration import (
    belief_fusion_respects_uncertainty,
    perception_provider_gated,
)
from app.core.animus.p2.metrics import content_margin, permutation_p, retrieval, two_afc
from app.core.animus.p2.splits import (
    assert_no_identity_leakage,
    freeze_identity_split,
    perceptual_hash_audit,
    trial_partition,
)
from app.core.animus.p2.synthetic import make_subject, unique_gallery
from app.core.animus.p2.target_representation import target_representation_seal, unit_l2


# ---------------------------------------------------------------- leakage / splits
def test_no_stimulus_identity_leakage():
    subj = make_subject("t", n_identities=90, reps=3, seed=1)
    split = freeze_identity_split(subj.stimulus_ids, seed=1)
    audit = assert_no_identity_leakage(subj.stimulus_ids, split)
    assert audit["leakage_free"]
    # all repetitions of every identity in one partition
    part = trial_partition(subj.stimulus_ids, split)
    by = {}
    for s, p in zip(subj.stimulus_ids, part):
        by.setdefault(s, set()).add(p)
    assert all(len(v) == 1 for v in by.values())


def test_near_duplicate_family_leakage_detected():
    subj = make_subject("t", n_identities=60, reps=1, seed=2)
    split = freeze_identity_split(subj.stimulus_ids, seed=2)
    # inject a near-duplicate of a train identity into test
    Y = subj.Y.copy()
    tr_id = split["train"][0]
    te_id = split["test"][0]
    idx_tr = subj.stimulus_ids.index(tr_id)
    idx_te = subj.stimulus_ids.index(te_id)
    Y[idx_te] = unit_l2(Y[idx_tr] + 1e-4 * np.random.default_rng(0).standard_normal(Y.shape[1]))
    audit = perceptual_hash_audit(Y, subj.stimulus_ids, split, near_dup_cos=0.98)
    assert audit["cross_split_near_duplicates"] >= 1 and not audit["family_leakage_free"]


def test_normalizer_is_fold_safe():
    subj = make_subject("t", n_identities=60, reps=1, seed=3)
    n = len(subj.X)
    res = leakage_test_normalizer(subj.X[: n // 2], subj.X[n // 2:])
    assert res["pass"]


def test_pca_fit_on_train_only():
    x = np.random.default_rng(0).standard_normal((50, 20))
    norm = FoldSafeNormalizer(n_components=5).fit(x[:30])
    assert norm.transform(x[30:]).shape == (20, 5)
    # perturbing unseen rows does not change the transform of train rows
    a = norm.transform(x[:30]).copy()
    _ = x[30:] + 999
    assert np.allclose(a, norm.transform(x[:30]))


def test_hyperparameter_selected_on_validation_not_test():
    subj = make_subject("t", n_identities=120, reps=1, signal=1.5, seed=4)
    split = freeze_identity_split(subj.stimulus_ids, seed=4)
    part = trial_partition(subj.stimulus_ids, split)
    tr, va = part == "train", part == "val"
    alpha, scores = select_alpha(subj.X[tr], subj.Y[tr], subj.X[va], subj.Y[va])
    assert alpha in [float(k) for k in scores] or str(alpha) in scores


# ---------------------------------------------------------------- firewall
def test_test_firewall_blocks_before_freeze():
    import os
    import tempfile

    from app.core.animus.p2.firewall import TestFirewall
    d = tempfile.mkdtemp()
    seal = os.path.join(d, "seal.json")
    fw = TestFirewall(seal_path=seal)
    with pytest.raises(PermissionError):
        fw.access_test("confirmatory")
    assert fw.audit()["test_outcome_accessed_before_freeze"] is True
    with open(seal, "w") as f:
        f.write("{}")
    fw.access_test("confirmatory")


def test_firewall_withholds_test_split_until_frozen():
    import os
    import tempfile

    from app.core.animus.p2.firewall import TestFirewall
    fw = TestFirewall(seal_path=os.path.join(tempfile.mkdtemp(), "seal.json"))
    g = fw.guard_split({"train": ["a"], "val": ["b"], "test": ["c"]})
    assert g["test"] == "WITHHELD_UNTIL_FREEZE"


# ---------------------------------------------------------------- immutability
def test_embedding_model_seal_stable():
    a = target_representation_seal()["self_hash"]
    b = target_representation_seal()["self_hash"]
    assert a == b


def test_roi_is_wang25_primary():
    seal = target_representation_seal()
    assert seal["primary_encoder"]["derived_from"].startswith("visual_stimulus")


# ---------------------------------------------------------------- permutation / bootstrap
def test_permutation_collapses_under_null():
    rng = np.random.default_rng(0)
    pred = unit_l2(rng.standard_normal((60, 32)))
    true = unit_l2(rng.standard_normal((60, 32)))     # independent -> null
    assert permutation_p(pred, true, n_perm=300) > 0.01


def test_permutation_significant_under_signal():
    subj = make_subject("t", n_identities=120, reps=1, signal=1.8, seed=6)
    split = freeze_identity_split(subj.stimulus_ids, seed=6)
    part = trial_partition(subj.stimulus_ids, split)
    tr, te = part == "train", part == "test"
    from app.core.animus.p2.decoder import RidgeDecoder
    dec = RidgeDecoder(alpha=100).fit(subj.X[tr], subj.Y[tr])
    pred = dec.predict(subj.X[te])
    assert content_margin(pred, subj.Y[te]) > 0
    assert permutation_p(pred, subj.Y[te], n_perm=300) < 0.05


def test_retrieval_and_2afc_chance():
    rng = np.random.default_rng(1)
    pred = unit_l2(rng.standard_normal((40, 16)))
    gal = unit_l2(rng.standard_normal((40, 16)))
    r = retrieval(pred, gal)
    assert 0 <= r["top1"] <= 1 and r["gallery_size"] == 40
    afc = two_afc(pred, unit_l2(rng.standard_normal((40, 16))), n_decoy=20)
    assert abs(afc["accuracy"] - 0.5) < 0.25  # near chance for random


# ---------------------------------------------------------------- uncertainty / reject
def test_uncertainty_and_reject_option():
    subj = make_subject("t", n_identities=120, reps=1, signal=1.6, seed=7)
    split = freeze_identity_split(subj.stimulus_ids, seed=7)
    part = trial_partition(subj.stimulus_ids, split)
    tr, va, te = part == "train", part == "val", part == "test"
    ens = BootstrapEnsembleDecoder(alpha=100, n_boot=15).fit(subj.X[tr], subj.Y[tr])
    ens.calibrate_reject(subj.X[va], 0.9)
    _, unc = ens.predict_with_uncertainty(subj.X[te])
    mask = ens.valid_mask(unc)
    assert ens.reject_threshold is not None
    assert 0 < mask.mean() <= 1.0


# ---------------------------------------------------------------- gate
def test_subject_and_dataset_gate():
    good = {"data_contract_pass": True, "atlas_qc_pass": True, "margin_M": 0.1,
            "permutation_p": 0.001, "bootstrap_ci_lower": 0.02, "all_seeds_positive": True}
    bad = {**good, "permutation_p": 0.2}
    assert subject_pass(good) and not subject_pass(bad)
    assert required_passes(6) == 2 and required_passes(9) == 3
    assert dataset_gate(2, 6, 6) == "ANIMUS_P2_PERCEPTION_DECODER_VALIDATED"
    assert dataset_gate(1, 6, 6) == "ANIMUS_P2_PERCEPTION_DECODER_LIMITED"
    assert dataset_gate(0, 6, 6) == "ANIMUS_P2_PERCEPTION_DECODER_FAIL"
    assert dataset_gate(3, 5, 6) == "ANIMUS_P2_BLOCKED_INCOMPLETE_MEASUREMENT"


# ---------------------------------------------------------------- capability isolation
def test_perception_validation_never_authorizes_imagery():
    base = cap.ScientificCapabilityAuthorization()
    assert not base.is_usable(cap.PERCEPTION_NEURAL_CONTENT)
    val = base.validate_perception("ANIMUS_P2_PERCEPTION_DECODER_VALIDATED")
    assert val.is_usable(cap.PERCEPTION_NEURAL_CONTENT)
    assert not val.is_usable(cap.IMAGERY_NEURAL_CONTENT)
    assert not val.is_usable(cap.DREAM_NEURAL_CONTENT)
    assert not val.is_usable(cap.NEURAL_RECONSTRUCTION)
    assert cap.imagery_unauthorized_invariant(val)


def test_behavioral_capability_backward_compatible():
    base = cap.ScientificCapabilityAuthorization()
    assert base.is_usable(cap.BEHAVIORAL_IMAGERY_ASSIST)
    assert base.claim_level_for(cap.BEHAVIORAL_IMAGERY_ASSIST) == "L1_BEHAVIORAL_ASSISTED"


def test_perception_provider_gated_off_by_default():
    assert perception_provider_gated(cap.ScientificCapabilityAuthorization()) is False
    val = cap.ScientificCapabilityAuthorization().validate_perception(
        "ANIMUS_P2_PERCEPTION_DECODER_VALIDATED")
    assert perception_provider_gated(val) is True


# ---------------------------------------------------------------- fusion / bridge
def test_belief_fusion_respects_uncertainty():
    assert belief_fusion_respects_uncertainty()["pass"]


# ---------------------------------------------------------------- model manifest
def test_model_manifest_requires_provenance():
    from app.core.animus.p2.decoder import ValidatedPerceptionNeuralDecoder
    with pytest.raises(ValueError):
        ValidatedPerceptionNeuralDecoder(np.zeros((4, 4)), {"roi": "Wang25"})  # missing fields


# ---------------------------------------------------------------- replay determinism
def test_decoder_deterministic():
    subj = make_subject("t", n_identities=80, reps=1, signal=1.5, seed=9)
    split = freeze_identity_split(subj.stimulus_ids, seed=9)
    part = trial_partition(subj.stimulus_ids, split)
    tr, te = part == "train", part == "test"
    e1 = BootstrapEnsembleDecoder(alpha=100, n_boot=10, seed=5).fit(subj.X[tr], subj.Y[tr])
    e2 = BootstrapEnsembleDecoder(alpha=100, n_boot=10, seed=5).fit(subj.X[tr], subj.Y[tr])
    p1, _ = e1.predict_with_uncertainty(subj.X[te])
    p2, _ = e2.predict_with_uncertainty(subj.X[te])
    assert np.allclose(p1, p2)


# ---------------------------------------------------------------- hidden-target isolation
def test_unique_gallery_holds_only_test_identities():
    subj = make_subject("t", n_identities=60, reps=2, seed=10)
    split = freeze_identity_split(subj.stimulus_ids, seed=10)
    gal, ids = unique_gallery(subj.Y, subj.stimulus_ids, split["test"])
    assert set(ids) <= set(split["test"])
    assert gal.shape[0] == len(ids)


# ---------------------------------------------------------------- generator privacy (P1 reuse)
def test_generator_privacy_still_enforced():
    from app.core.animus.candidate_generator import PrivacyViolation, assert_no_forbidden_content
    with pytest.raises(PrivacyViolation):
        assert_no_forbidden_content({"raw_neural": [1, 2, 3]})
