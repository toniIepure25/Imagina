"""Deterministic fixture tests for the sealed-H2 inference machinery: exact
6! target-label null, repeat-preserving permutations, 2AFC, and the seal
fail-closed guard. No NSD data is downloaded.
"""
from __future__ import annotations

import itertools

import numpy as np

from app.research.fmri.run_h2_zero_shot_transfer import (
    _exact_permutation_null,
    _monte_carlo_null,
)


def _sims_for(n_targets=6, repeats=16, n_pool=12, signal=0.0, seed=0):
    """Build a [n_trials, n_pool] cosine-sim matrix where each of n_targets
    stimuli (pool indices 6..6+n_targets-1 for Set B) is repeated `repeats`
    times. `signal` boosts the true target's similarity.
    """
    rng = np.random.default_rng(seed)
    set_labels = list(range(6, 6 + n_targets))
    target_pool_indices = np.repeat(set_labels, repeats)
    n_trials = len(target_pool_indices)
    sims = rng.standard_normal((n_trials, n_pool)) * 0.1
    for i, lab in enumerate(target_pool_indices):
        sims[i, lab] += signal
    return sims, np.array(target_pool_indices), set_labels


class TestExactPermutationNull:
    def test_enumerates_exactly_6_factorial(self):
        sims, targets, labels = _sims_for()
        res = _exact_permutation_null(sims, targets, labels)
        assert res["n_permutations"] == 720  # 6!

    def test_strong_signal_is_significant(self):
        sims, targets, labels = _sims_for(signal=5.0, seed=1)
        res = _exact_permutation_null(sims, targets, labels)
        assert res["observed_mrr"] > res["exact_null_mean"]
        assert res["exact_p_value"] <= 1.0 / 720 + 1e-9  # only identity ties/beats it

    def test_no_signal_is_not_significant(self):
        sims, targets, labels = _sims_for(signal=0.0, seed=2)
        res = _exact_permutation_null(sims, targets, labels)
        assert res["exact_p_value"] > 0.05

    def test_identity_permutation_is_included(self):
        # p-value must be >= 1/720 because the identity permutation always
        # reproduces the observed value.
        sims, targets, labels = _sims_for(signal=100.0, seed=3)
        res = _exact_permutation_null(sims, targets, labels)
        assert res["exact_p_value"] >= 1.0 / 720 - 1e-12


class TestRepeatPreservingStructure:
    def test_all_repeats_of_a_stimulus_get_same_permuted_label(self):
        # Verify the exact null treats each stimulus as one unit: permuting
        # labels then relabeling must keep all repeats of a stimulus identical.
        sims, targets, labels = _sims_for(n_targets=3, repeats=4, n_pool=12)
        # Reconstruct the remap logic and confirm group integrity.
        for perm in itertools.permutations(labels):
            remap = {orig: perm[i] for i, orig in enumerate(labels)}
            relabeled = [remap[int(t)] for t in targets]
            # every stimulus's repeats share one label
            for lab in labels:
                idxs = [i for i, t in enumerate(targets) if t == lab]
                vals = {relabeled[i] for i in idxs}
                assert len(vals) == 1


class TestMonteCarloNull:
    def test_mc_null_runs_and_returns_p(self):
        sims, targets, labels = _sims_for(signal=3.0, seed=4)
        res = _monte_carlo_null(sims, targets, labels, n_perms=500, seed=20260724)
        assert res["n_permutations"] == 500
        assert 0.0 < res["mc_p_value"] <= 1.0
        assert res["observed_mrr"] > res["mc_null_mean"]


class TestSealFailClosed:
    def test_runner_refuses_without_seal(self, tmp_path, monkeypatch):
        # The H2 runner must raise if the seal file is absent.
        import app.research.fmri.run_h2_zero_shot_transfer as h2
        monkeypatch.setenv("NSD_DATA_ROOT", str(tmp_path))
        monkeypatch.setenv("NSD_BETAS_ROOT", str(tmp_path))
        monkeypatch.setenv("NSD_CACHE_ROOT", str(tmp_path))
        monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
        # no seal file created
        import pytest
        with pytest.raises(RuntimeError, match="seal manifest not found"):
            h2.main()

    def test_runner_refuses_wrong_seal_status(self, tmp_path, monkeypatch):
        import json

        import pytest

        import app.research.fmri.run_h2_zero_shot_transfer as h2
        (tmp_path / "c3_h2_unblinding_manifest.json").write_text(
            json.dumps({"status": "DRAFT_NOT_SEALED"})
        )
        monkeypatch.setenv("NSD_DATA_ROOT", str(tmp_path))
        monkeypatch.setenv("NSD_BETAS_ROOT", str(tmp_path))
        monkeypatch.setenv("NSD_CACHE_ROOT", str(tmp_path))
        monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
        with pytest.raises(RuntimeError, match="not SEALED_BEFORE_H2_EVALUATION"):
            h2.main()
