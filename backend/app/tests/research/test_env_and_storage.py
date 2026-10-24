"""Tests for environment variable enforcement and storage budget.

Proves:
- Unset NSD_STIMULI_ROOT fails closed
- Configured valid path succeeds
- Configured missing path fails clearly
- No machine-specific fallback exists in module code
- Storage budget calculation is correct
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from app.research.fmri.clip_provenance import check_stimuli_availability
from app.research.fmri.storage_budget import compute_storage_budget


class TestStimuliRootEnforcement:
    def test_unset_variable_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("NSD_STIMULI_ROOT", None)
            result = check_stimuli_availability()
            assert result["status"] == "BLOCKED_STIMULI_ROOT_NOT_CONFIGURED"
            assert "NSD_STIMULI_ROOT" in result["error"]

    def test_configured_valid_path_succeeds(self, tmp_path):
        img_dir = tmp_path / "stimuli"
        img_dir.mkdir()
        (img_dir / "test.png").write_bytes(b"fake_image")
        result = check_stimuli_availability(stimuli_root=img_dir)
        assert result["status"] == "AVAILABLE"
        assert result["n_images_found"] >= 1

    def test_configured_missing_path_fails_clearly(self, tmp_path):
        missing = tmp_path / "nonexistent"
        result = check_stimuli_availability(stimuli_root=missing)
        assert result["exists"] is False
        assert "BLOCKED" in result["status"] or "NOT_AVAILABLE" in result["status"]

    def test_no_machine_specific_fallback_in_source(self):
        import inspect
        source = inspect.getsource(check_stimuli_availability)
        assert "ComputaCenter" not in source
        assert "FMRI2images" not in source
        assert r"D:\\" not in source


class TestStorageBudget:
    def test_budget_requires_env_or_path(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("NSD_BETAS_ROOT", None)
            result = compute_storage_budget()
            assert result["status"] == "BLOCKED_CONFIGURATION"

    def test_budget_with_valid_dir(self, tmp_path):
        betas_dir = tmp_path / "ppdata" / "subj01" / "func1pt8mm" / "betas_fithrf"
        betas_dir.mkdir(parents=True)
        for s in range(1, 6):
            f = betas_dir / f"betas_session{s:02d}.hdf5"
            f.write_bytes(b"\x00" * 1_094_445_528)

        result = compute_storage_budget(betas_dir)
        assert result["sessions_complete"] == 5
        assert result["sessions_remaining"] == 35
        assert "current_free_gb" in result
        assert "post_completion_free_gb" in result
        assert result["status"] in ("PASS", "BLOCKED_INSUFFICIENT_DISK")

    def test_budget_reports_all_fields(self, tmp_path):
        betas_dir = tmp_path / "ppdata" / "subj01" / "func1pt8mm" / "betas_fithrf"
        betas_dir.mkdir(parents=True)
        result = compute_storage_budget(betas_dir)

        required_fields = [
            "current_free_bytes", "sessions_complete", "sessions_remaining",
            "remaining_download_bytes", "roi_cache_bytes", "clip_embeddings_bytes",
            "model_checkpoint_bytes", "temporary_headroom_bytes",
            "total_required_bytes", "post_completion_free_bytes", "sufficient",
        ]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"


class TestNoHardcodedPaths:
    """Verify no machine-specific paths exist in module source code."""

    def _get_module_source(self, module_path: str) -> str:
        full_path = Path(__file__).parent.parent.parent / "research" / "fmri" / module_path
        return full_path.read_text(encoding="utf-8")

    @pytest.mark.parametrize("module_file", [
        "clip_provenance.py",
        "readiness_gate.py",
        "run_c3_realdata.py",
        "inspect_sessions.py",
        "download_perception_betas.py",
        "stimulus_mapping.py",
        "spatial_alignment.py",
        "memory_safe.py",
        "split_manifest.py",
        "joint_randomization.py",
        "storage_budget.py",
    ])
    def test_no_hardcoded_local_paths(self, module_file):
        source = self._get_module_source(module_file)
        assert "ComputaCenter" not in source, f"{module_file} contains hardcoded path"
        assert "FMRI2images" not in source, f"{module_file} contains hardcoded path"
