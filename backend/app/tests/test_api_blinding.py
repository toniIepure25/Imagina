"""Tests for API information separation — public vs operator views."""
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage.database import init_db

client = TestClient(app)

FORBIDDEN_PUBLIC_FIELDS = [
    "condition_sequence",
    "randomization_seed",
    "sequence_id",
    "current_condition",
    "future_condition",
    "yoked_source",
    "policy_identifier",
]


@pytest.fixture(autouse=True)
def _setup_db(monkeypatch, tmp_path):
    db_path = os.path.join(str(tmp_path), "test_blinding.db")
    monkeypatch.setattr("app.storage.database.DB_PATH", db_path)
    monkeypatch.setattr("app.core.config.settings.study_mode", "pilot")
    import asyncio
    loop = asyncio.new_event_loop()
    loop.run_until_complete(init_db())
    loop.close()


class TestCapabilitiesEndpoint:
    def test_returns_capabilities(self):
        resp = client.get("/api/research-protocol/capabilities")
        assert resp.status_code == 200
        data = resp.json()
        assert "study_mode" in data
        assert "database_foreign_keys_enabled" in data
        assert data["human_collection_allowed"] is False
        assert "migration_version" in data

    def test_fk_enabled(self):
        resp = client.get("/api/research-protocol/capabilities")
        data = resp.json()
        assert data["database_foreign_keys_enabled"] is True


class TestPublicParticipantView:
    def _create_study_and_participant(self):
        client.post("/api/research-protocol/operator/studies", json={
            "study_id": "s1",
            "title": "Test Study",
            "protocol_version": "1.0",
            "conditions": ["adaptive", "fixed", "yoked"],
            "description": "test",
            "ethics_status": "not_submitted",
            "ethics_reference": "",
        })
        resp = client.post("/api/research-protocol/operator/studies/s1/participants", json={
            "pseudonym": "ALICE",
            "study_id": "s1",
            "eligibility_confirmed": True,
        })
        return resp.json()

    def test_public_view_has_no_forbidden_fields(self):
        op_data = self._create_study_and_participant()
        pid = op_data["participant_id"]
        resp = client.get(f"/api/research-protocol/public/participants/{pid}")
        assert resp.status_code == 200
        data = resp.json()
        for field in FORBIDDEN_PUBLIC_FIELDS:
            assert field not in data, f"Public view should not contain '{field}'"

    def test_operator_view_contains_sequence(self):
        op_data = self._create_study_and_participant()
        pid = op_data["participant_id"]
        resp = client.get(f"/api/research-protocol/operator/participants/{pid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "condition_sequence" in data
        assert "randomization_seed" in data

    def test_public_view_not_found(self):
        resp = client.get("/api/research-protocol/public/participants/nonexistent")
        assert resp.status_code == 404
