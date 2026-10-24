"""Studio persistence and service loop: save, reload, resume, branch, world."""
from __future__ import annotations

import pathlib
import shutil
import tempfile

import pytest

from app.core.animus.scene.compose import shade
from app.core.animus.scene.model import SceneGraph
from app.core.animus.studio.repository import StudioRepository
from app.core.animus.studio.service import AnimusStudioService, StudioValidationError

pytestmark = pytest.mark.core


@pytest.fixture
async def service():
    directory = tempfile.mkdtemp(prefix="animus-studio-")
    repo = StudioRepository(str(pathlib.Path(directory) / "studio.db"))
    yield AnimusStudioService(repository=repo)
    shutil.rmtree(directory, ignore_errors=True)


async def _create(service: AnimusStudioService, intention: str = "a white castle above a dark ocean at dusk") -> dict:
    return await service.create_session(title="Castle study", intention=intention, seed=17)


async def test_create_persist_and_reload(service):
    created = await _create(service)
    assert created["session_id"].startswith("ast_")
    assert created["claim_level"] == "L1_BEHAVIORAL_ASSISTED"
    assert created["capabilities"]["neural_content"] == "UNAUTHORIZED"
    assert created["scene"]["entities"]
    session_id = created["session_id"]
    head_hash = created["scene"]["metadata"]["content_hash"]

    reopened = AnimusStudioService(repository=StudioRepository(service.repository._path()))
    loaded = await reopened.get_session(session_id)
    assert loaded["scene"]["metadata"]["content_hash"] == head_hash
    assert loaded["history"][0]["version_id"] == created["active_version_id"]


async def test_event_sequence_is_monotonic_and_reported(service):
    created = await _create(service)
    session_id = created["session_id"]
    assert created["last_event_seq"] >= 1

    updated = await service.apply_intent(session_id, "make the sky deep violet")
    assert updated["last_event_seq"] > created["last_event_seq"]

    events = await service.events(session_id)
    seqs = [event["seq"] for event in events["events"]]
    assert seqs == sorted(seqs)
    assert seqs[-1] == updated["last_event_seq"]

    reopened = AnimusStudioService(repository=StudioRepository(service.repository._path()))
    reloaded = await reopened.get_session(session_id)
    assert reloaded["last_event_seq"] == updated["last_event_seq"]


async def test_multiple_sessions_keep_independent_branch_history(service):
    first = await _create(service, "a white castle above a dark ocean at dusk")
    second = await _create(service, "a red moon over a pale forest")
    await service.apply_intent(first["session_id"], "make the sky deep violet")
    await service.apply_intent(second["session_id"], "add a second moon")

    reopened = AnimusStudioService(repository=StudioRepository(service.repository._path()))
    loaded_first = await reopened.get_session(first["session_id"])
    loaded_second = await reopened.get_session(second["session_id"])
    assert loaded_first["version"]["number"] == 2
    assert loaded_second["version"]["number"] == 2
    assert loaded_first["active_branch_id"] == "main"
    assert loaded_second["active_branch_id"] == "main"
    assert loaded_first["history"][0]["version_id"] == first["active_version_id"]
    assert loaded_second["history"][0]["version_id"] == second["active_version_id"]
    assert loaded_first["active_version_id"] != loaded_second["active_version_id"]


async def test_reload_prefers_session_active_version_over_stale_branch_head(service):
    created = await _create(service)
    session_id = created["session_id"]
    await service.apply_intent(session_id, "make the sky deep violet")
    history = await service.history(session_id)
    stale_branch = dict(history["branches"][0])
    stale_branch["session_id"] = session_id
    stale_branch["head_version_id"] = created["active_version_id"]
    await service.repository.save_branch(stale_branch)

    reopened = AnimusStudioService(repository=StudioRepository(service.repository._path()))
    loaded = await reopened.get_session(session_id)
    assert loaded["version"]["number"] == 2
    assert loaded["scene"]["atmosphere"]["sky"]["top"] == shade("#8a5cf0", 0.35)


async def test_intent_creates_new_immutable_version(service):
    created = await _create(service)
    session_id = created["session_id"]
    root_hash = created["scene"]["metadata"]["content_hash"]
    updated = await service.apply_intent(session_id, "make the sky deep violet")
    assert updated["version"]["number"] == 2
    assert updated["scene"]["metadata"]["content_hash"] != root_hash
    assert updated["scene"]["atmosphere"]["sky"]["top"] == shade("#8a5cf0", 0.35)
    assert updated["resolutions"]
    history = await service.history(session_id)
    assert len(history["versions"]) == 2
    assert history["has_undo"] is True


async def test_locked_color_survives_regeneration_and_candidate_selection(service):
    created = await _create(service)
    session_id = created["session_id"]
    locked = await service.apply_intent(session_id, "lock the castle color")
    castle = next(e for e in locked["scene"]["entities"] if e["kind"] == "castle")
    color = castle["attributes"]["color"]["value"]

    generated = await service.regenerate(session_id, count=3, seed=5)
    assert len(generated["generated"]) == 3
    for candidate in generated["generated"]:
        candidate_castle = next(e for e in candidate["scene"]["entities"] if e["kind"] == "castle")
        assert candidate_castle["attributes"]["color"]["value"] == color

    selected = await service.select_candidate(session_id, generated["generated"][0]["candidate_id"])
    assert selected["version"]["source"] == "candidate"
    selected_castle = next(e for e in selected["scene"]["entities"] if e["kind"] == "castle")
    assert selected_castle["attributes"]["color"]["value"] == color


async def test_undo_redo_roundtrip_through_service(service):
    created = await _create(service)
    session_id = created["session_id"]
    root_hash = created["scene"]["metadata"]["content_hash"]
    await service.apply_intent(session_id, "make the sky deep violet")
    undone = await service.undo(session_id)
    assert undone["scene"]["metadata"]["content_hash"] == root_hash
    redone = await service.redo(session_id)
    assert redone["scene"]["atmosphere"]["sky"]["top"] == shade("#8a5cf0", 0.35)


async def test_branch_and_switch(service):
    created = await _create(service)
    session_id = created["session_id"]
    main_hash = created["scene"]["metadata"]["content_hash"]
    branched = await service.branch(session_id, name="violet sky")
    assert branched["active_branch_name"] == "violet sky"
    assert branched["scene"]["metadata"]["content_hash"] == main_hash
    await service.apply_intent(session_id, "make the sky deep violet")
    violet_hash = (await service.get_session(session_id))["scene"]["metadata"]["content_hash"]
    switched = await service.switch_branch(session_id, "main")
    assert switched["scene"]["metadata"]["content_hash"] == main_hash
    back = await service.switch_branch(session_id, branched["active_branch_id"])
    assert back["scene"]["metadata"]["content_hash"] == violet_hash


async def test_world_save_list_open_delete(service):
    created = await _create(service)
    session_id = created["session_id"]
    world = await service.save_world(session_id, name="Castle world", description="A castle over water")
    assert world["items"]
    listed = await service.list_worlds()
    assert any(item["world_id"] == world["world_id"] for item in listed["worlds"])
    opened = await service.open_world(world["world_id"])
    assert opened["session_id"] != session_id
    assert opened["scene"]["metadata"]["content_hash"] == created["scene"]["metadata"]["content_hash"]
    await service.delete_world(world["world_id"])
    with pytest.raises(Exception):
        await service.get_world(world["world_id"])


async def test_claim_guard_rejects_mind_reading_copy(service):
    with pytest.raises(StudioValidationError):
        await service.create_session(title="Mind reading demo", intention="a castle", seed=1)
    with pytest.raises(StudioValidationError):
        await service.create_session(title="Castle", intention="show me what I am imagining", seed=1)


async def test_delete_session(service):
    created = await _create(service)
    result = await service.delete_session(created["session_id"])
    assert result["deleted"] == created["session_id"]
    with pytest.raises(Exception):
        await service.get_session(created["session_id"])


async def test_reloaded_scene_is_valid_scene_graph(service):
    created = await _create(service)
    reopened = AnimusStudioService(repository=StudioRepository(service.repository._path()))
    loaded = await reopened.get_session(created["session_id"])
    scene = SceneGraph.from_dict(loaded["scene"])
    assert scene.content_hash() == loaded["scene"]["metadata"]["content_hash"]


async def test_redo_survives_restart(service):
    created = await _create(service)
    session_id = created["session_id"]
    await service.apply_intent(session_id, "make the sky deep violet")
    undone = await service.undo(session_id)
    assert undone["has_redo"] is True

    reopened = AnimusStudioService(repository=StudioRepository(service.repository._path()))
    loaded = await reopened.get_session(session_id)
    assert loaded["has_redo"] is True
    redone = await reopened.redo(session_id)
    assert redone["scene"]["atmosphere"]["sky"]["top"] == shade("#8a5cf0", 0.35)
    assert redone["has_redo"] is False


async def test_new_commit_clears_redo_across_restart(service):
    created = await _create(service)
    session_id = created["session_id"]
    await service.apply_intent(session_id, "make the sky deep violet")
    await service.undo(session_id)
    await service.apply_intent(session_id, "make the sky pale gold")

    reopened = AnimusStudioService(repository=StudioRepository(service.repository._path()))
    loaded = await reopened.get_session(session_id)
    assert loaded["has_redo"] is False
