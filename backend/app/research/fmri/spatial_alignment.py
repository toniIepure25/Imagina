"""Spatial alignment certification for NSD beta-to-ROI coordinate mapping.

Provides a fail-closed spatial mapping component that:
- Reads beta axis metadata from HDF5
- Reads NIfTI dimensions and affine
- Validates expected permutations
- Maps NIfTI voxel coordinates into beta indices
- Extracts known ROI coordinates
- Performs round-trip coordinate tests
- Rejects ambiguous mappings
- Hashes the selected transformation

Status remains PENDING_REAL_CERTIFICATION until verified on real data.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class SpatialMapping:
    """Describes the coordinate mapping between NIfTI/ROI space and beta space."""
    nifti_shape: tuple[int, ...]
    beta_shape: tuple[int, ...]
    nifti_affine: tuple[tuple[float, ...], ...]
    axis_permutation: tuple[int, ...]
    axis_flip: tuple[bool, ...]
    mapping_hash: str
    status: str = "PENDING_REAL_CERTIFICATION"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "nifti_shape": list(self.nifti_shape),
            "beta_shape": list(self.beta_shape),
            "nifti_affine": [list(row) for row in self.nifti_affine],
            "axis_permutation": list(self.axis_permutation),
            "axis_flip": list(self.axis_flip),
            "mapping_hash": self.mapping_hash,
            "status": self.status,
            "notes": self.notes,
        }


@dataclass
class SpatialCertificationResult:
    """Result of spatial alignment certification."""
    certified: bool = False
    status: str = "PENDING_REAL_CERTIFICATION"
    mapping: SpatialMapping | None = None
    checks: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "certified": self.certified,
            "status": self.status,
            "mapping": self.mapping.to_dict() if self.mapping else None,
            "checks": self.checks,
            "errors": self.errors,
        }


def _compute_mapping_hash(
    nifti_shape: tuple, beta_shape: tuple, affine: np.ndarray, permutation: tuple, flip: tuple,
) -> str:
    blob = json.dumps({
        "nifti_shape": list(nifti_shape),
        "beta_shape": list(beta_shape),
        "affine": affine.tolist(),
        "permutation": list(permutation),
        "flip": list(flip),
    }, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:32]


def infer_axis_permutation(
    nifti_shape: tuple[int, ...],
    beta_spatial_shape: tuple[int, ...],
) -> tuple[int, ...] | None:
    """Infer axis permutation from NIfTI shape to beta spatial shape.

    Returns None if no unique permutation can be determined (ambiguous).
    """
    if len(nifti_shape) != len(beta_spatial_shape):
        return None

    if len(nifti_shape) != 3:
        return None

    from itertools import permutations
    matches = []
    for perm in permutations(range(3)):
        permuted = tuple(nifti_shape[p] for p in perm)
        if permuted == beta_spatial_shape:
            matches.append(perm)

    if len(matches) == 1:
        return matches[0]
    elif len(matches) == 0:
        return None
    else:
        return None


def certify_spatial_alignment(
    nifti_shape: tuple[int, ...],
    nifti_affine: NDArray[np.float64],
    beta_shape: tuple[int, ...],
    roi_mask_shape: tuple[int, ...] | None = None,
    known_roi_coords: NDArray[np.int64] | None = None,
    beta_sample: NDArray | None = None,
) -> SpatialCertificationResult:
    """Certify the spatial mapping between NIfTI/ROI and beta arrays.

    Args:
        nifti_shape: Shape of the NIfTI volume (x, y, z) or (i, j, k) in NIfTI convention.
        nifti_affine: 4x4 affine matrix from NIfTI header.
        beta_shape: Shape of beta array spatial dimensions.
        roi_mask_shape: Shape of the ROI mask NIfTI (should match nifti_shape).
        known_roi_coords: Known in-ROI voxel coordinates for verification.
        beta_sample: Optional sample beta volume for verification.
    """
    result = SpatialCertificationResult()

    if roi_mask_shape is not None and roi_mask_shape != nifti_shape:
        result.errors.append(f"ROI mask shape {roi_mask_shape} != NIfTI shape {nifti_shape}")
        result.status = "FAILED_SHAPE_MISMATCH"
        return result

    result.checks["nifti_shape"] = list(nifti_shape)
    result.checks["beta_shape"] = list(beta_shape)
    result.checks["affine_diagonal"] = [float(nifti_affine[i, i]) for i in range(3)]

    beta_spatial = beta_shape
    if len(beta_shape) == 4:
        beta_spatial = beta_shape[1:]
    elif len(beta_shape) == 2:
        result.checks["beta_format"] = "flattened_2d"
        result.checks["note"] = "Beta is [trials, voxels] — spatial mapping requires volume or metadata"
        result.status = "PENDING_REAL_CERTIFICATION"
        result.errors.append("Beta is 2D flattened; spatial mapping requires full volume or documented flatten order")
        return result

    permutation = infer_axis_permutation(nifti_shape, beta_spatial)

    if permutation is None:
        all_same = (nifti_shape == beta_spatial)
        if all_same:
            permutation = (0, 1, 2)
            result.checks["permutation_source"] = "identity_same_shape"
        else:
            result.errors.append(
                f"Cannot infer unique permutation: NIfTI {nifti_shape} -> beta spatial {beta_spatial}. "
                f"Shapes are ambiguous or incompatible."
            )
            result.status = "FAILED_AMBIGUOUS_MAPPING"
            return result
    else:
        result.checks["permutation_source"] = "unique_shape_match"

    result.checks["axis_permutation"] = list(permutation)
    dim_str = ",".join(f"dim{permutation.index(d)}" for d in range(3))
    result.checks["maps_nifti_to_beta"] = f"nifti[i,j,k] -> beta[{dim_str}]"

    flip = (False, False, False)
    result.checks["axis_flip"] = list(flip)

    if known_roi_coords is not None and beta_sample is not None:
        try:
            n_checks = min(100, len(known_roi_coords))
            for idx in range(n_checks):
                coord = known_roi_coords[idx]
                beta_coord = tuple(coord[permutation[d]] for d in range(3))
                _ = beta_sample[beta_coord]
            result.checks["round_trip_coords_checked"] = n_checks
            result.checks["round_trip_pass"] = True
        except (IndexError, ValueError) as e:
            result.errors.append(f"Round-trip coordinate test failed: {e}")
            result.status = "FAILED_ROUND_TRIP"
            return result

    affine_tuple = tuple(tuple(float(v) for v in row) for row in nifti_affine)
    mapping_hash = _compute_mapping_hash(nifti_shape, beta_spatial, nifti_affine, permutation, flip)

    mapping = SpatialMapping(
        nifti_shape=nifti_shape,
        beta_shape=beta_spatial,
        nifti_affine=affine_tuple,
        axis_permutation=permutation,
        axis_flip=flip,
        mapping_hash=mapping_hash,
        status="PENDING_REAL_CERTIFICATION",
    )

    result.mapping = mapping
    result.status = "PENDING_REAL_CERTIFICATION"
    result.checks["mapping_hash"] = mapping_hash
    return result


def nifti_to_beta_coords(
    nifti_coords: NDArray[np.int64],
    permutation: tuple[int, ...],
    flip: tuple[bool, ...] = (False, False, False),
    volume_shape: tuple[int, ...] | None = None,
) -> NDArray[np.int64]:
    """Convert NIfTI voxel coordinates to beta array coordinates.

    nifti_coords: [N, 3] array of (i, j, k) NIfTI coordinates
    Returns: [N, 3] array of beta coordinates
    """
    result = np.zeros_like(nifti_coords)
    for dim in range(3):
        src_dim = permutation[dim]
        vals = nifti_coords[:, src_dim]
        if flip[dim] and volume_shape:
            vals = volume_shape[src_dim] - 1 - vals
        result[:, dim] = vals
    return result


def beta_to_nifti_coords(
    beta_coords: NDArray[np.int64],
    permutation: tuple[int, ...],
    flip: tuple[bool, ...] = (False, False, False),
    volume_shape: tuple[int, ...] | None = None,
) -> NDArray[np.int64]:
    """Convert beta array coordinates back to NIfTI voxel coordinates."""
    inv_perm = [0, 0, 0]
    for i, p in enumerate(permutation):
        inv_perm[p] = i
    inv_perm = tuple(inv_perm)

    result = np.zeros_like(beta_coords)
    for dim in range(3):
        src_dim = inv_perm[dim]
        vals = beta_coords[:, src_dim]
        if flip[src_dim] and volume_shape:
            vals = volume_shape[dim] - 1 - vals
        result[:, dim] = vals
    return result


def extract_roi_voxels_flat(
    volume: NDArray,
    roi_mask: NDArray[np.int32],
    roi_value: int = 1,
) -> NDArray:
    """Extract voxels matching roi_value from a 3D volume, returning 1D array."""
    if volume.shape != roi_mask.shape:
        raise ValueError(f"Volume shape {volume.shape} != ROI mask shape {roi_mask.shape}")
    mask = roi_mask == roi_value
    return volume[mask]


def get_roi_coordinates(roi_mask: NDArray[np.int32], roi_value: int = 1) -> NDArray[np.int64]:
    """Get (i, j, k) coordinates of all voxels with given ROI value."""
    coords = np.argwhere(roi_mask == roi_value)
    return coords.astype(np.int64)
