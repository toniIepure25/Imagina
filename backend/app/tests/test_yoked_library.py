"""Tests for frozen yoked trajectory library."""
import os
import tempfile

import aiosqlite
import pytest

from app.research.yoked_library import (
    YokedLibraryFrozenError,
    YokedLibraryValidationError,
    assign_trajectory,
    create_library,
    freeze_library,
    generate_trajectories,
    get_trajectory_points,
    validate_library,
)
from app.storage.migration_runner import run_migrations


@pytest.fixture
async def yoked_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "yoked_test.db")
        db = await aiosqlite.connect(path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        await run_migrations(db)
        await db.execute(
            "INSERT INTO studies (study_id, title, created_at, updated_at) "
            "VALUES ('s1', 'Test', '2026-01-01', '2026-01-01')"
        )
        await db.execute(
            "INSERT INTO protocol_versions (protocol_version_id, study_id, version, status, created_at) "
            "VALUES ('pv1', 's1', '1.0', 'frozen', '2026-01-01')"
        )
        await db.commit()
        yield db
        await db.close()


class TestYokedLibraryLifecycle:
    async def test_create_and_freeze(self, yoked_db):
        lib_id = await create_library(yoked_db, "s1", "pv1", "sched_abc", 42)
        await generate_trajectories(yoked_db, lib_id, 3, 5, "sched_abc")
        await freeze_library(yoked_db, lib_id)

        row = await (await yoked_db.execute(
            "SELECT status, content_hash FROM frozen_yoked_libraries WHERE library_id = ?",
            (lib_id,),
        )).fetchone()
        assert row["status"] == "frozen"
        assert row["content_hash"] is not None

    async def test_frozen_library_immutable(self, yoked_db):
        lib_id = await create_library(yoked_db, "s1", "pv1", "sched_abc", 42)
        await generate_trajectories(yoked_db, lib_id, 2, 4, "sched_abc")
        await freeze_library(yoked_db, lib_id)

        with pytest.raises(YokedLibraryFrozenError):
            await generate_trajectories(yoked_db, lib_id, 1, 4, "sched_abc")

    async def test_validate_passes(self, yoked_db):
        lib_id = await create_library(yoked_db, "s1", "pv1", "sched_abc", 42)
        await generate_trajectories(yoked_db, lib_id, 2, 3, "sched_abc")
        await freeze_library(yoked_db, lib_id)

        result = await validate_library(yoked_db, lib_id, "sched_abc")
        assert result is True

    async def test_validate_wrong_schedule(self, yoked_db):
        lib_id = await create_library(yoked_db, "s1", "pv1", "sched_abc", 42)
        await generate_trajectories(yoked_db, lib_id, 2, 3, "sched_abc")
        await freeze_library(yoked_db, lib_id)

        with pytest.raises(YokedLibraryValidationError, match="Schedule hash mismatch"):
            await validate_library(yoked_db, lib_id, "wrong_hash")

    async def test_validate_unfrozen_fails(self, yoked_db):
        lib_id = await create_library(yoked_db, "s1", "pv1", "sched_abc", 42)
        await generate_trajectories(yoked_db, lib_id, 2, 3, "sched_abc")

        with pytest.raises(YokedLibraryValidationError, match="not frozen"):
            await validate_library(yoked_db, lib_id, "sched_abc")

    async def test_deterministic_assignment(self, yoked_db):
        lib_id = await create_library(yoked_db, "s1", "pv1", "sched_abc", 42)
        await generate_trajectories(yoked_db, lib_id, 6, 4, "sched_abc")
        await freeze_library(yoked_db, lib_id)

        t1 = await assign_trajectory(yoked_db, lib_id, 42, "p1", 0)
        t2 = await assign_trajectory(yoked_db, lib_id, 42, "p1", 0)
        assert t1 == t2

    async def test_different_participants_different_trajectories(self, yoked_db):
        lib_id = await create_library(yoked_db, "s1", "pv1", "sched_abc", 42)
        await generate_trajectories(yoked_db, lib_id, 6, 4, "sched_abc")
        await freeze_library(yoked_db, lib_id)

        assignments = set()
        for i in range(6):
            t = await assign_trajectory(yoked_db, lib_id, 42, f"p{i}", 0)
            assignments.add(t)
        assert len(assignments) > 1

    async def test_get_trajectory_points(self, yoked_db):
        lib_id = await create_library(yoked_db, "s1", "pv1", "sched_abc", 42)
        traj_ids = await generate_trajectories(yoked_db, lib_id, 1, 5, "sched_abc")

        points = await get_trajectory_points(yoked_db, traj_ids[0])
        assert len(points) == 5
        assert "scene_params" in points[0]
        assert "scene_clarity" in points[0]["scene_params"]

    async def test_empty_library_cannot_freeze(self, yoked_db):
        lib_id = await create_library(yoked_db, "s1", "pv1", "sched_abc", 42)
        with pytest.raises(YokedLibraryValidationError, match="empty"):
            await freeze_library(yoked_db, lib_id)
