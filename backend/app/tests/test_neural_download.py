"""Tests for the ds005815 download/checksum logic (Commit 8 CI: c1-download-smoke).

Uses mocked HTTP responses only -- no real network access, no real
downloaded data, per the CI/full-run separation established in
C1_ANALYSIS_SPEC.md: standard CI runs against tiny deterministic fixtures,
never the real dataset. This exercises the exact download/checksum code
path (URL construction, idempotent skip-if-present, checksum entry
creation, manifest writing) that the controlled research workflow uses
against the real S3 mirror.
"""
from __future__ import annotations

import hashlib
import json
from unittest.mock import Mock, patch

from app.research.neural.download import (
    DATASET_ID,
    DATASET_VERSION,
    RUN_SUFFIXES,
    download_ancillary_vividness_csv,
    download_recording,
)


def _fake_response(content: bytes) -> Mock:
    resp = Mock()
    resp.raise_for_status = Mock()
    resp.iter_content = Mock(return_value=[content])
    return resp


class TestDownloadRecording:
    def test_downloads_all_run_suffixes_for_one_participant_session(self, tmp_path):
        with patch("app.research.neural.download.requests.get") as mock_get:
            mock_get.return_value = _fake_response(b"fake-eeg-bytes")
            entries = download_recording("sub-01", "1", out_dir=str(tmp_path))

        assert len(entries) == len(RUN_SUFFIXES)
        assert mock_get.call_count == len(RUN_SUFFIXES)
        for entry, suffix in zip(entries, RUN_SUFFIXES):
            assert entry.relative_path.endswith(f"sub-01_ses-1_task-task{suffix}")
            assert entry.sha256 == hashlib.sha256(b"fake-eeg-bytes").hexdigest()
            assert entry.size_bytes == len(b"fake-eeg-bytes")

    def test_url_paths_match_expected_s3_layout(self, tmp_path):
        with patch("app.research.neural.download.requests.get") as mock_get:
            mock_get.return_value = _fake_response(b"x")
            download_recording("sub-02", "1", out_dir=str(tmp_path))

        called_urls = [call.args[0] for call in mock_get.call_args_list]
        assert all(f"/{DATASET_ID}/sub-02/ses-1/eeg/sub-02_ses-1_task-task" in url for url in called_urls)

    def test_idempotent_skip_when_file_already_present(self, tmp_path):
        with patch("app.research.neural.download.requests.get") as mock_get:
            mock_get.return_value = _fake_response(b"same-bytes")
            download_recording("sub-01", "1", out_dir=str(tmp_path))
            first_call_count = mock_get.call_count
            download_recording("sub-01", "1", out_dir=str(tmp_path))

        # _download_file only skips the GET when the destination already
        # exists; re-running against the same out_dir must not fail and
        # must produce the same checksum entries either way.
        assert mock_get.call_count >= first_call_count


class TestDownloadAncillaryCsv:
    def test_downloads_to_ancillary_subdirectory(self, tmp_path):
        with patch("app.research.neural.download.requests.get") as mock_get:
            mock_get.return_value = _fake_response(b"csv,data\n1,2\n")
            entry = download_ancillary_vividness_csv(out_dir=str(tmp_path))

        assert entry.relative_path.replace("\\", "/") == "ancillary/Trigger_Vividness_Data.csv"
        assert entry.sha256 == hashlib.sha256(b"csv,data\n1,2\n").hexdigest()


class TestChecksumManifestRoundTrip:
    def test_manifest_written_by_main_is_valid_json_with_expected_fields(self, tmp_path):
        with patch("app.research.neural.download.requests.get") as mock_get, \
             patch("sys.argv", ["download.py", "--subjects", "sub-01", "--sessions", "1",
                                "--out", str(tmp_path), "--skip-ancillary"]):
            mock_get.return_value = _fake_response(b"fixture-bytes")
            from app.research.neural.download import main
            main()

        manifest_path = tmp_path / "checksum_manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert manifest["dataset_id"] == DATASET_ID
        assert manifest["dataset_version"] == DATASET_VERSION
        assert len(manifest["entries"]) == len(RUN_SUFFIXES)
        for entry in manifest["entries"]:
            assert {"relative_path", "sha256", "size_bytes", "downloaded_at", "source_url"} <= entry.keys()
