"""Tests for balanced Williams crossover sequence allocator."""
import os
import tempfile

import aiosqlite
import pytest

from app.research.governance import AllocationIntegrityError
from app.research.sequence_allocator import (
    WILLIAMS_SEQUENCES,
    allocate_sequence,
    get_allocation,
    verify_williams_balance,
)
from app.storage.migration_runner import run_migrations


@pytest.fixture
async def alloc_db(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "alloc_test.db")
        monkeypatch.setattr("app.storage.database.DB_PATH", path)
        db = await aiosqlite.connect(path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await run_migrations(db)
        await db.execute(
            "INSERT INTO studies (study_id, title, study_seed, created_at, updated_at) "
            "VALUES ('s1', 'Test', 42, '2026-01-01', '2026-01-01')"
        )
        for i in range(12):
            await db.execute(
                "INSERT INTO participants (participant_id, study_id, pseudonym, created_at) "
                f"VALUES ('p{i}', 's1', 'P{i:03d}', '2026-01-01')"
            )
        await db.commit()
        await db.close()
        yield path


class TestWilliamsBalance:
    def test_position_balance(self):
        report = verify_williams_balance()
        assert report["position_balanced"] is True

    def test_carryover_balance(self):
        report = verify_williams_balance()
        assert report["carryover_balanced"] is True

    def test_six_sequences(self):
        assert len(WILLIAMS_SEQUENCES) == 6


class TestAllocation:
    async def test_deterministic_from_seed(self, alloc_db):
        label1, seq1 = await allocate_sequence("s1", "p0", 42)
        label2, seq2 = await allocate_sequence("s1", "p0", 42)
        assert label1 == label2
        assert seq1 == seq2

    async def test_balanced_across_six(self, alloc_db):
        labels = []
        for i in range(6):
            label, _ = await allocate_sequence("s1", f"p{i}", 42)
            labels.append(label)
        from collections import Counter
        counts = Counter(labels)
        assert max(counts.values()) - min(counts.values()) <= 1

    async def test_balanced_across_twelve(self, alloc_db):
        labels = []
        for i in range(12):
            label, _ = await allocate_sequence("s1", f"p{i}", 42)
            labels.append(label)
        from collections import Counter
        counts = Counter(labels)
        assert all(c == 2 for c in counts.values())

    async def test_immutable_after_allocation(self, alloc_db):
        label1, _ = await allocate_sequence("s1", "p0", 42)
        label2, _ = await allocate_sequence("s1", "p0", 42)
        assert label1 == label2

    async def test_get_allocation_returns_assigned(self, alloc_db):
        label, seq = await allocate_sequence("s1", "p0", 42)
        result = await get_allocation("s1", "p0")
        assert result is not None
        assert result[0] == label

    async def test_get_allocation_returns_none_unassigned(self, alloc_db):
        result = await get_allocation("s1", "p0")
        assert result is None

    async def test_incomplete_cohort_balance(self, alloc_db):
        labels = []
        for i in range(4):
            label, _ = await allocate_sequence("s1", f"p{i}", 42)
            labels.append(label)
        from collections import Counter
        counts = Counter(labels)
        assert max(counts.values()) - min(counts.values()) <= 1

    async def test_corrupted_sequence_label_raises(self, alloc_db):
        await allocate_sequence("s1", "p0", 42)
        db = await aiosqlite.connect(alloc_db)
        await db.execute(
            "UPDATE sequence_allocations SET sequence_label='INVALID' "
            "WHERE study_id='s1' AND participant_id='p0'"
        )
        await db.commit()
        await db.close()

        with pytest.raises(AllocationIntegrityError, match="INVALID"):
            await allocate_sequence("s1", "p0", 42)

    async def test_corrupted_label_in_get_allocation_raises(self, alloc_db):
        await allocate_sequence("s1", "p0", 42)
        db = await aiosqlite.connect(alloc_db)
        await db.execute(
            "UPDATE sequence_allocations SET sequence_label='CORRUPT' "
            "WHERE study_id='s1' AND participant_id='p0'"
        )
        await db.commit()
        await db.close()

        with pytest.raises(AllocationIntegrityError, match="CORRUPT"):
            await get_allocation("s1", "p0")
