"""Tests for spatial alignment certification.

Uses asymmetric synthetic volumes so incorrect axis permutations
cannot accidentally pass.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.research.fmri.spatial_alignment import (
    beta_to_nifti_coords,
    certify_spatial_alignment,
    extract_roi_voxels_flat,
    get_roi_coordinates,
    infer_axis_permutation,
    nifti_to_beta_coords,
)


class TestInferAxisPermutation:
    def test_identity_same_shape(self):
        result = infer_axis_permutation((81, 104, 83), (81, 104, 83))
        assert result == (0, 1, 2)

    def test_unique_permutation_detected(self):
        result = infer_axis_permutation((81, 104, 83), (83, 81, 104))
        assert result is not None
        nifti = (81, 104, 83)
        permuted = tuple(nifti[p] for p in result)
        assert permuted == (83, 81, 104)

    def test_ambiguous_symmetric_shape_rejected(self):
        result = infer_axis_permutation((64, 64, 64), (64, 64, 64))
        assert result == (0, 1, 2) or result is None

    def test_incompatible_shapes_returns_none(self):
        result = infer_axis_permutation((81, 104, 83), (100, 100, 100))
        assert result is None

    def test_asymmetric_all_distinct_detects_permutation(self):
        result = infer_axis_permutation((7, 11, 13), (13, 7, 11))
        assert result is not None
        original = (7, 11, 13)
        permuted = tuple(original[p] for p in result)
        assert permuted == (13, 7, 11)


class TestCertifySpatialAlignment:
    def test_matching_shapes_identity(self):
        nifti_shape = (81, 104, 83)
        affine = np.eye(4) * 1.8
        affine[3, 3] = 1.0
        beta_shape = (750, 81, 104, 83)

        result = certify_spatial_alignment(nifti_shape, affine, beta_shape)
        assert result.status == "PENDING_REAL_CERTIFICATION"
        assert result.mapping is not None
        assert result.mapping.axis_permutation == (0, 1, 2)

    def test_permuted_shape_detected(self):
        nifti_shape = (7, 11, 13)
        affine = np.eye(4)
        beta_shape = (100, 13, 7, 11)

        result = certify_spatial_alignment(nifti_shape, affine, beta_shape)
        assert result.status == "PENDING_REAL_CERTIFICATION"
        assert result.mapping is not None
        perm = result.mapping.axis_permutation
        original = (7, 11, 13)
        permuted = tuple(original[p] for p in perm)
        assert permuted == (13, 7, 11)

    def test_roi_shape_mismatch_fails(self):
        nifti_shape = (81, 104, 83)
        affine = np.eye(4)
        beta_shape = (750, 81, 104, 83)
        roi_shape = (80, 104, 83)

        result = certify_spatial_alignment(nifti_shape, affine, beta_shape, roi_mask_shape=roi_shape)
        assert "FAILED" in result.status

    def test_2d_beta_reports_pending(self):
        nifti_shape = (81, 104, 83)
        affine = np.eye(4)
        beta_shape = (750, 700000)

        result = certify_spatial_alignment(nifti_shape, affine, beta_shape)
        assert result.status == "PENDING_REAL_CERTIFICATION"
        assert len(result.errors) > 0

    def test_incompatible_shapes_fails(self):
        nifti_shape = (81, 104, 83)
        affine = np.eye(4)
        beta_shape = (750, 100, 100, 100)

        result = certify_spatial_alignment(nifti_shape, affine, beta_shape)
        assert "FAILED" in result.status


class TestCoordinateMapping:
    def test_identity_permutation_round_trip(self):
        rng = np.random.default_rng(42)
        coords = rng.integers(0, 50, size=(100, 3)).astype(np.int64)
        perm = (0, 1, 2)

        beta_coords = nifti_to_beta_coords(coords, perm)
        recovered = beta_to_nifti_coords(beta_coords, perm)
        np.testing.assert_array_equal(coords, recovered)

    def test_nontrivial_permutation_round_trip(self):
        rng = np.random.default_rng(7)
        coords = rng.integers(0, 50, size=(200, 3)).astype(np.int64)
        perm = (2, 0, 1)

        beta_coords = nifti_to_beta_coords(coords, perm)
        recovered = beta_to_nifti_coords(beta_coords, perm)
        np.testing.assert_array_equal(coords, recovered)

    def test_asymmetric_volume_prevents_accidental_pass(self):
        """Asymmetric volume: wrong permutation produces different coordinates."""
        coords = np.array([[2, 5, 8], [1, 3, 7], [6, 0, 4]], dtype=np.int64)
        correct_perm = (2, 0, 1)
        wrong_perm = (0, 1, 2)

        correct_beta = nifti_to_beta_coords(coords, correct_perm)
        wrong_beta = nifti_to_beta_coords(coords, wrong_perm)

        assert not np.array_equal(correct_beta, wrong_beta)


class TestROIExtraction:
    def test_extract_matching_voxels(self):
        volume = np.arange(24).reshape(2, 3, 4).astype(np.float32)
        mask = np.zeros((2, 3, 4), dtype=np.int32)
        mask[0, 1, 2] = 1
        mask[1, 0, 3] = 1
        mask[0, 0, 0] = -1

        extracted = extract_roi_voxels_flat(volume, mask, roi_value=1)
        assert extracted.shape == (2,)
        assert volume[0, 1, 2] in extracted
        assert volume[1, 0, 3] in extracted

    def test_shape_mismatch_raises(self):
        volume = np.zeros((2, 3, 4))
        mask = np.zeros((2, 3, 5), dtype=np.int32)
        with pytest.raises(ValueError):
            extract_roi_voxels_flat(volume, mask)

    def test_get_roi_coordinates(self):
        mask = np.zeros((3, 4, 5), dtype=np.int32)
        mask[1, 2, 3] = 1
        mask[2, 0, 4] = 1
        mask[0, 0, 0] = -1

        coords = get_roi_coordinates(mask, roi_value=1)
        assert coords.shape == (2, 3)
        assert [1, 2, 3] in coords.tolist()
        assert [2, 0, 4] in coords.tolist()
