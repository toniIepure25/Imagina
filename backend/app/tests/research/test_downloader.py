"""Deterministic fixture tests for download_perception_betas.

Tests cover: interrupted downloads, resume, truncated responses,
wrong remote sizes, corrupted completed files, lock behavior, and
atomic manifest writes. Does NOT hit the real NSD endpoint.
"""
from __future__ import annotations

import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

from app.research.fmri.download_perception_betas import (
    _acquire_lock,
    _release_lock,
    _write_manifest_atomic,
    check_disk_space,
    download_with_resume,
    get_remote_size,
    sha256_file,
)

FIXTURE_CONTENT = b"x" * 10240  # 10 KB fixture data
FIXTURE_HASH = hashlib.sha256(FIXTURE_CONTENT).hexdigest()


class MockNSDHandler(BaseHTTPRequestHandler):
    """HTTP handler that simulates NSD S3 responses for testing."""

    server_content: bytes = FIXTURE_CONTENT
    simulate_truncate: bool = False
    simulate_ignore_range: bool = False
    simulate_wrong_size: bool = False

    def log_message(self, format, *args):
        pass

    def do_HEAD(self):
        size = len(self.server_content)
        if self.__class__.simulate_wrong_size:
            size = size + 999
        self.send_response(200)
        self.send_header("Content-Length", str(size))
        self.end_headers()

    def do_GET(self):
        content = self.server_content
        range_header = self.headers.get("Range")

        if range_header and not self.__class__.simulate_ignore_range:
            start = int(range_header.split("=")[1].split("-")[0])
            self.send_response(206)
            remaining = content[start:]
            if self.__class__.simulate_truncate:
                remaining = remaining[: len(remaining) // 2]
            self.send_header("Content-Length", str(len(remaining)))
            self.end_headers()
            self.wfile.write(remaining)
        elif range_header and self.__class__.simulate_ignore_range:
            self.send_response(200)
            data = content
            if self.__class__.simulate_truncate:
                data = data[: len(data) // 2]
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(200)
            data = content
            if self.__class__.simulate_truncate:
                data = data[: len(data) // 2]
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)


@pytest.fixture()
def mock_server():
    """Start a local HTTP server for download tests."""
    MockNSDHandler.server_content = FIXTURE_CONTENT
    MockNSDHandler.simulate_truncate = False
    MockNSDHandler.simulate_ignore_range = False
    MockNSDHandler.simulate_wrong_size = False

    server = HTTPServer(("127.0.0.1", 0), MockNSDHandler)
    port = server.server_address[1]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture()
def tmp_download_dir(tmp_path):
    d = tmp_path / "downloads"
    d.mkdir()
    return d


class TestCompleteDownload:
    def test_fresh_download_succeeds(self, mock_server, tmp_download_dir):
        dest = tmp_download_dir / "test.hdf5"
        url = f"{mock_server}/test.hdf5"
        result = download_with_resume(url, dest, expected_size=len(FIXTURE_CONTENT), max_retries=1)
        assert result is True
        assert dest.exists()
        assert dest.stat().st_size == len(FIXTURE_CONTENT)
        assert sha256_file(dest) == FIXTURE_HASH

    def test_already_complete_skips(self, mock_server, tmp_download_dir):
        dest = tmp_download_dir / "test.hdf5"
        dest.write_bytes(FIXTURE_CONTENT)
        url = f"{mock_server}/test.hdf5"
        result = download_with_resume(url, dest, expected_size=len(FIXTURE_CONTENT), max_retries=1)
        assert result is True


class TestResumeDownload:
    def test_resume_from_partial(self, mock_server, tmp_download_dir):
        dest = tmp_download_dir / "test.hdf5"
        partial = dest.with_suffix(".hdf5.part")
        half = FIXTURE_CONTENT[: len(FIXTURE_CONTENT) // 2]
        partial.write_bytes(half)

        url = f"{mock_server}/test.hdf5"
        result = download_with_resume(url, dest, expected_size=len(FIXTURE_CONTENT), max_retries=1)
        assert result is True
        assert dest.exists()
        assert dest.stat().st_size == len(FIXTURE_CONTENT)

    def test_resume_server_ignores_range_restarts(self, mock_server, tmp_download_dir):
        MockNSDHandler.simulate_ignore_range = True
        dest = tmp_download_dir / "test.hdf5"
        partial = dest.with_suffix(".hdf5.part")
        partial.write_bytes(FIXTURE_CONTENT[:100])

        url = f"{mock_server}/test.hdf5"
        result = download_with_resume(url, dest, expected_size=len(FIXTURE_CONTENT), max_retries=1)
        assert result is True
        assert dest.stat().st_size == len(FIXTURE_CONTENT)


class TestTruncatedResponse:
    def test_truncated_download_fails(self, mock_server, tmp_download_dir):
        MockNSDHandler.simulate_truncate = True
        dest = tmp_download_dir / "test.hdf5"
        url = f"{mock_server}/test.hdf5"
        result = download_with_resume(url, dest, expected_size=len(FIXTURE_CONTENT), max_retries=1)
        assert result is False
        assert not dest.exists()


class TestWrongRemoteSize:
    def test_wrong_remote_size_detected(self, mock_server, tmp_download_dir):
        MockNSDHandler.simulate_wrong_size = True
        url = f"{mock_server}/test.hdf5"
        remote_size = get_remote_size(url)
        assert remote_size != len(FIXTURE_CONTENT)


class TestCorruptedFile:
    def test_size_mismatch_triggers_redownload(self, mock_server, tmp_download_dir):
        dest = tmp_download_dir / "test.hdf5"
        dest.write_bytes(b"corrupted_short")
        url = f"{mock_server}/test.hdf5"
        result = download_with_resume(url, dest, expected_size=len(FIXTURE_CONTENT), max_retries=2)
        assert result is True
        assert dest.stat().st_size == len(FIXTURE_CONTENT)

    def test_oversized_partial_removed(self, mock_server, tmp_download_dir):
        dest = tmp_download_dir / "test.hdf5"
        partial = dest.with_suffix(".hdf5.part")
        partial.write_bytes(b"x" * (len(FIXTURE_CONTENT) + 500))
        url = f"{mock_server}/test.hdf5"
        result = download_with_resume(url, dest, expected_size=len(FIXTURE_CONTENT), max_retries=2)
        assert result is True
        assert dest.stat().st_size == len(FIXTURE_CONTENT)


class TestLockBehavior:
    def test_lock_acquire_release(self, tmp_download_dir):
        lock_path = tmp_download_dir / ".download_lock"
        assert _acquire_lock(lock_path) is True
        assert lock_path.exists()
        content = json.loads(lock_path.read_text())
        assert content["pid"] == os.getpid()
        _release_lock(lock_path)
        assert not lock_path.exists()

    def test_lock_rejects_live_pid(self, tmp_download_dir):
        lock_path = tmp_download_dir / ".download_lock"
        lock_path.write_text(json.dumps({"pid": os.getpid(), "started": "2026-01-01T00:00:00"}))
        assert _acquire_lock(lock_path) is False

    def test_lock_overrides_dead_pid(self, tmp_download_dir):
        lock_path = tmp_download_dir / ".download_lock"
        lock_path.write_text(json.dumps({"pid": 99999999, "started": "2026-01-01T00:00:00"}))
        assert _acquire_lock(lock_path) is True


class TestManifestAtomicWrite:
    def test_atomic_write_creates_file(self, tmp_download_dir):
        manifest_path = tmp_download_dir / "manifest.json"
        data = {"status": "ok", "count": 5}
        _write_manifest_atomic(data, manifest_path)
        assert manifest_path.exists()
        loaded = json.loads(manifest_path.read_text())
        assert loaded == data
        tmp = manifest_path.with_suffix(".json.tmp")
        assert not tmp.exists()


class TestDiskSpaceCheck:
    def test_sufficient_space_passes(self, tmp_download_dir):
        result = check_disk_space(tmp_download_dir, sessions_remaining=1)
        assert result is True

    def test_zero_remaining_passes(self, tmp_download_dir):
        result = check_disk_space(tmp_download_dir, sessions_remaining=0)
        assert result is True


class TestIdempotentSkip:
    def test_certified_file_not_redownloaded(self, mock_server, tmp_download_dir):
        dest = tmp_download_dir / "test.hdf5"
        dest.write_bytes(FIXTURE_CONTENT)
        url = f"{mock_server}/test.hdf5"
        result = download_with_resume(url, dest, expected_size=len(FIXTURE_CONTENT), max_retries=1)
        assert result is True
        assert sha256_file(dest) == FIXTURE_HASH
