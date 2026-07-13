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
            db1_path = os.path.join(tmpdir, "run1.db")
            db2_path = os.path.join(tmpdir, "run2.db")

            await run_synthetic_study(
                db_path=db1_path, study_id="replay-test",
                participant_count=2, seed=42,
                trials_per_session=2, windows_per_trial=2,
            )
            await run_synthetic_study(
                db_path=db2_path, study_id="replay-test",
                participant_count=2, seed=42,
                trials_per_session=2, windows_per_trial=2,
            )

            db1 = await aiosqlite.connect(db1_path)
            db1.row_factory = aiosqlite.Row
            db2 = await aiosqlite.connect(db2_path)
            db2.row_factory = aiosqlite.Row

            cursor = await db1.execute(
                "SELECT research_session_id FROM research_sessions LIMIT 1"
            )
            row = await cursor.fetchone()
            session_id = row["research_session_id"]

            result = await verify_replay_equivalence(db1, db2, session_id)
            await db1.close()
            await db2.close()

            assert result["match"] is True

    async def test_different_seeds_diverge(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db1_path = os.path.join(tmpdir, "run1.db")
            db2_path = os.path.join(tmpdir, "run2.db")

            await run_synthetic_study(
                db_path=db1_path, study_id="div-test",
                participant_count=2, seed=42,
                trials_per_session=2, windows_per_trial=2,
            )
            await run_synthetic_study(
                db_path=db2_path, study_id="div-test",
                participant_count=2, seed=99,
                trials_per_session=2, windows_per_trial=2,
            )

            db1 = await aiosqlite.connect(db1_path)
            db1.row_factory = aiosqlite.Row
            db2 = await aiosqlite.connect(db2_path)
            db2.row_factory = aiosqlite.Row

            cursor = await db1.execute(
                "SELECT research_session_id FROM research_sessions LIMIT 1"
            )
            row = await cursor.fetchone()
            session_id = row["research_session_id"]

            result = await verify_replay_equivalence(db1, db2, session_id)
            await db1.close()
            await db2.close()

            assert result["match"] is False
            assert "divergence" in result

    async def test_session_hash_stable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "stable.db")

            await run_synthetic_study(
                db_path=db_path, study_id="hash-test",
                participant_count=2, seed=42,
                trials_per_session=2, windows_per_trial=2,
            )

            db = await aiosqlite.connect(db_path)
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT research_session_id FROM research_sessions LIMIT 1"
            )
            row = await cursor.fetchone()
            session_id = row["research_session_id"]

            h1 = await compute_session_replay_hash(db, session_id)
            h2 = await compute_session_replay_hash(db, session_id)
            await db.close()

            assert h1["content_hash"] == h2["content_hash"]


class TestReplayFromManifest:
    async def test_replay_fixed_session(self):
        """Fixed-condition sessions should replay identically from manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "orig.db")

            await run_synthetic_study(
                db_path=db_path, study_id="manifest-replay",
                participant_count=2, seed=42,
                trials_per_session=2, windows_per_trial=2,
            )

            db = await aiosqlite.connect(db_path)
            db.row_factory = aiosqlite.Row

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

            await db.close()
