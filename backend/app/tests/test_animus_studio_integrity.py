"""Concurrency, lifecycle, and migration-integrity checks for ANIMUS Studio."""
from __future__ import annotations

import asyncio
import pathlib
import shutil
import tempfile

import aiosqlite
import pytest

from app.core.animus.studio.errors import StudioArchived, StudioConflict, StudioCorruptState
from app.core.animus.studio.repository import StudioRepository
from app.core.animus.studio.service import AnimusStudioService

pytestmark = pytest.mark.core


@pytest.fixture
async def service():
    directory = tempfile.mkdtemp(prefix="animus-studio-integrity-")
    repo = StudioRepository(str(pathlib.Path(directory) / "studio.db"))
    yield AnimusStudioService(repository=repo)
    shutil.rmtree(directory, ignore_errors=True)


async def _create(service: AnimusStudioService) -> dict:
    return await service.create_session(
        title="Integrity", intention="a white castle above a dark ocean at dusk", seed=29)


async def test_schema_reaches_v017(service):
    assert await service.repository.schema_version() == 17


async def test_expected_version_is_optimistic_and_atomic(service):
    created = await _create(service)
    session_id = created["session_id"]
    head = created["active_version_id"]

    updated = await service.apply_intent(
        session_id, "make the sky deep violet", expected_version_id=head)
    assert updated["version"]["number"] == 2

    with pytest.raises(StudioConflict):
        await service.apply_intent(
            session_id, "make the sky deep violet", expected_version_id=head)

    latest = await service.get_session(session_id)
    assert latest["version"]["number"] == 2


async def test_archived_session_rejects_mutations(service):
    created = await _create(service)
    session_id = created["session_id"]
    await service.repository.update_session(
        session_id, updated_at=created["updated_at"], status="archived")

    reopened = AnimusStudioService(repository=StudioRepository(service.repository._path()))
    with pytest.raises(StudioArchived):
        await reopened.apply_intent(session_id, "make the sky deep violet")


async def test_candidates_are_scoped_to_their_source_version(service):
    created = await _create(service)
    session_id = created["session_id"]
    generated = await service.regenerate(session_id, count=2, seed=11)
    candidate_id = generated["generated"][0]["candidate_id"]
    source_version_id = generated["source_version_id"]

    await service.apply_intent(session_id, "make the sky deep violet")
    refreshed = await service.get_session(session_id)
    assert refreshed["candidates"] == []
    with pytest.raises(StudioConflict):
        await service.select_candidate(session_id, candidate_id)

    stored = await service.repository.load_candidates(
        session_id, source_version_id=source_version_id, include_selected=False)
    assert any(item["candidate_id"] == candidate_id for item in stored)


async def test_selected_candidate_is_hidden_after_reload(service):
    created = await _create(service)
    session_id = created["session_id"]
    generated = await service.regenerate(session_id, count=1, seed=13)
    candidate_id = generated["generated"][0]["candidate_id"]
    selected = await service.select_candidate(session_id, candidate_id)
    assert selected["version"]["source"] == "candidate"

    reopened = AnimusStudioService(repository=StudioRepository(service.repository._path()))
    loaded = await reopened.get_session(session_id)
    assert loaded["candidates"] == []
    stored = await reopened.repository.get_candidate(session_id, candidate_id)
    assert stored is not None and stored["selected"] is True


async def test_concurrent_expected_version_has_one_winner(service):
    created = await _create(service)
    session_id = created["session_id"]
    head = created["active_version_id"]

    results = await asyncio.gather(
        *(
            service.apply_intent(
                session_id, "make the sky deep violet", expected_version_id=head)
            for _ in range(4)
        ),
        return_exceptions=True,
    )
    winners = [item for item in results if isinstance(item, dict)]
    conflicts = [item for item in results if isinstance(item, StudioConflict)]
    assert len(winners) == 1
    assert len(conflicts) == 3
    assert (await service.get_session(session_id))["version"]["number"] == 2


async def test_corrupt_scene_is_reported_as_corruption(service):
    created = await _create(service)
    session_id = created["session_id"]
    async with aiosqlite.connect(service.repository._path()) as db:
        await db.execute(
            "UPDATE animus_studio_versions SET scene_json = '{' WHERE session_id = ?",
            (session_id,),
        )
        await db.commit()

    reopened = AnimusStudioService(repository=StudioRepository(service.repository._path()))
    with pytest.raises(StudioCorruptState):
        await reopened.get_session(session_id)


async def test_wrong_json_shape_is_reported_as_corruption(service):
    created = await _create(service)
    session_id = created["session_id"]
    async with aiosqlite.connect(service.repository._path()) as db:
        await db.execute(
            "UPDATE animus_studio_versions SET scene_json = '[]' WHERE session_id = ?",
            (session_id,),
        )
        await db.commit()

    reopened = AnimusStudioService(repository=StudioRepository(service.repository._path()))
    with pytest.raises(StudioCorruptState):
        await reopened.get_session(session_id)


async def test_corrupt_event_payload_is_not_a_server_error(service):
    created = await _create(service)
    session_id = created["session_id"]
    async with aiosqlite.connect(service.repository._path()) as db:
        await db.execute(
            "UPDATE animus_studio_events SET payload_json = '[]' WHERE session_id = ?",
            (session_id,),
        )
        await db.commit()

    reopened = AnimusStudioService(repository=StudioRepository(service.repository._path()))
    with pytest.raises(StudioCorruptState):
        await reopened.events(session_id)


async def test_pragmas_use_durable_local_settings(service):
    diagnostics = await service.repository.diagnostics()
    assert diagnostics["journal_mode"] == "wal"
    assert diagnostics["synchronous"] == 2
    assert diagnostics["foreign_keys"] is True


async def test_deep_diagnostics_reports_integrity(service):
    diagnostics = await service.repository.diagnostics(deep=True)
    assert diagnostics["integrity"] == "ok"
    assert diagnostics["foreign_key_violations"] == 0
