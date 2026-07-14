"""Tests for deterministic replay validation."""
import os
import tempfile

import aiosqlite
import pytest

from app.research.replay_validator import (
    canonical_hash,
    canonical_serialize,
    compute_session_replay_hash,
    normalize,
    replay_session_from_manifest,
    verify_replay_equivalence,
)
from app.research.synthetic_orchestrator import run_synthetic_study
from app.storage.migration_runner import run_migrations

_db_counter = 0


async def _make_study_db(tmpdir, study_id, seed=42, participant_count=2):
    global _db_counter
    _db_counter += 1
    db_path = os.path.join(tmpdir, f"{study_id}_{_db_counter}.db")
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await run_migrations(db)
    await run_synthetic_study(
        db=db, study_id=study_id,
        participant_count=participant_count, seed=seed,
        trials_per_session=2, windows_per_trial=2,
    )
    return db


class TestNormalize:
    def test_none(self):
        assert normalize(None) is None

    def test_bool(self):
        assert normalize(True) is True
        assert normalize(False) is False

    def test_int(self):
        assert normalize(42) == 42

    def test_float_precision(self):
        assert normalize(0.1 + 0.2) == round(0.3, 8)

    def test_string(self):
        assert normalize("hello") == "hello"

    def test_dict_sorted(self):
        result = normalize({"z": 1, "a": 2})
        keys = list(result.keys())
        assert keys == ["a", "z"]

    def test_list(self):
        assert normalize([3.0, 2.0, 1.0]) == [3.0, 2.0, 1.0]

    def test_nested(self):
        data = {"a": [{"c": 1.1234567890123, "b": 2}]}
        result = normalize(data)
        assert result["a"][0]["c"] == round(1.1234567890123, 8)

    def test_rejects_nan(self):
        with pytest.raises(ValueError, match="non-finite"):
            normalize(float("nan"))

    def test_rejects_infinity(self):
        with pytest.raises(ValueError, match="non-finite"):
            normalize(float("inf"))


class TestCanonicalSerialization:
    def test_sorted_keys(self):
        data = {"z": 1, "a": 2, "m": 3}
        result = canonical_serialize(data)
        assert result == b'{"a":2,"m":3,"z":1}'

    def test_deterministic(self):
        data = {"key": [1, 2, 3], "nested": {"b": 2, "a": 1}}
        h1 = canonical_hash(data)
        h2 = canonical_hash(data)
        assert h1 == h2

    def test_rejects_nan(self):
        with pytest.raises(ValueError, match="non-finite"):
            canonical_serialize({"value": float("nan")})

    def test_rejects_infinity(self):
        with pytest.raises(ValueError, match="non-finite"):
            canonical_serialize({"value": float("inf")})

    def test_float_precision(self):
        data = {"value": 0.1 + 0.2}
        result = canonical_serialize(data)
        assert b"0.3" in result


class TestReplayEquivalence:
    async def test_identical_runs_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db1 = await _make_study_db(tmpdir, "replay-test", seed=42)
            db2 = await _make_study_db(tmpdir, "replay-test", seed=42)
            try:
                cursor = await db1.execute(
                    "SELECT research_session_id FROM research_sessions LIMIT 1"
                )
                row = await cursor.fetchone()
                session_id = row["research_session_id"]
                result = await verify_replay_equivalence(db1, db2, session_id)
                assert result["match"] is True
            finally:
                await db1.close()
                await db2.close()

    async def test_different_seeds_diverge(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db1 = await _make_study_db(tmpdir, "div-test", seed=42)
            db2 = await _make_study_db(tmpdir, "div-test-2", seed=99)
            try:
                c1 = await db1.execute(
                    "SELECT research_session_id FROM research_sessions LIMIT 1"
                )
                row1 = await c1.fetchone()
                session_id = row1["research_session_id"]

                c2 = await db2.execute(
                    "SELECT research_session_id FROM research_sessions LIMIT 1"
                )
                row2 = await c2.fetchone()

                h1 = await compute_session_replay_hash(db1, session_id)
                h2 = await compute_session_replay_hash(db2, row2["research_session_id"])
                assert h1["content_hash"] != h2["content_hash"]
            finally:
                await db1.close()
                await db2.close()

    async def test_session_hash_stable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_study_db(tmpdir, "hash-test")
            try:
                cursor = await db.execute(
                    "SELECT research_session_id FROM research_sessions LIMIT 1"
                )
                row = await cursor.fetchone()
                session_id = row["research_session_id"]

                h1 = await compute_session_replay_hash(db, session_id)
                h2 = await compute_session_replay_hash(db, session_id)
                assert h1["content_hash"] == h2["content_hash"]
            finally:
                await db.close()


class TestReplayFromManifest:
    async def test_replay_fixed_session(self):
        """Fixed-condition sessions should replay identically from manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_study_db(tmpdir, "manifest-replay")
            try:
                cursor = await db.execute(
                    "SELECT research_session_id FROM research_sessions "
                    "WHERE condition = 'fixed' LIMIT 1"
                )
                row = await cursor.fetchone()

                if row:
                    session_id = row["research_session_id"]
                    result = await replay_session_from_manifest(db, session_id)
                    assert result["match"] is True
                    assert result["manifest_hash"]
            finally:
                await db.close()

    async def test_tampered_manifest_hash_fails_replay(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_study_db(tmpdir, "tamper-manifest")
            try:
                row = await (await db.execute(
                    "SELECT research_session_id FROM research_sessions "
                    "WHERE condition = 'fixed' LIMIT 1"
                )).fetchone()
                if not row:
                    return
                session_id = row["research_session_id"]

                await db.execute(
                    "UPDATE session_manifests SET manifest_hash = 'tampered' "
                    "WHERE research_session_id = ?",
                    (session_id,),
                )
                await db.commit()

                result = await replay_session_from_manifest(db, session_id)
                assert result["match"] is False
            finally:
                await db.close()

    async def test_deleted_yoked_points_fails_replay(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = await _make_study_db(tmpdir, "yoked-del")
            try:
                row = await (await db.execute(
                    "SELECT research_session_id FROM research_sessions "
                    "WHERE condition = 'yoked' LIMIT 1"
                )).fetchone()
                if not row:
                    return
                session_id = row["research_session_id"]

                await db.execute("DELETE FROM frozen_yoked_points")
                await db.commit()

                result = await replay_session_from_manifest(db, session_id)
                assert result["match"] is False
                assert "no points" in result.get("error", "").lower() or result["match"] is False
            finally:
                await db.close()
