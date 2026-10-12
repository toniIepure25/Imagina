import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.multimodal.protocols import (
    design_operating_characteristics,
    run_protocol_a,
    run_protocol_b,
    run_protocol_c,
    run_protocol_causal,
)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr("app.storage.database.DB_PATH", str(tmp_path / "mm.db"))


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_modalities_lists_all_seven(client):
    r = await client.get("/api/multimodal/modalities")
    body = r.json()
    assert r.status_code == 200 and len(body["modalities"]) == 7
    assert {p["source_kind"] for p in body["providers"]} == {"SYNTHETIC", "REPLAY", "REAL_SENSOR"}


async def test_session_run_timeline_sync_and_replay(client):
    r = await client.post("/api/multimodal/sessions", json={"session_id": "api-a", "duration_s": 70})
    assert r.status_code == 200
    summ = r.json()
    assert summ["mode"] == "shadow" and summ["n_delivered"] == 0 and summ["trace_valid"]
    tl = (await client.get("/api/multimodal/sessions/api-a/timeline")).json()
    assert len(tl["ticks"]) == 35
    last = tl["ticks"][-1]
    assert last["dimensions"]["vividness"]["evidence"] == "SUBJECTIVE_REPORT"
    assert "ecg" in last["features"] and last["scene"]["prompt_text"]
    sync = (await client.get("/api/multimodal/sessions/api-a/sync")).json()
    assert sync["current"]["n_streams"] == 5 and "alignment_note" in sync["current"]
    rv = (await client.post("/api/multimodal/sessions/api-a/replay-verify")).json()
    assert rv["reproduced"] and rv["final_hash"] == rv["original_final_hash"]
    corridor = (await client.get("/api/multimodal/sessions/api-a/corridor/latest")).json()
    assert {"scene", "audio", "policy_version", "triggering_estimate", "safety_decision"} <= set(corridor)


async def test_live_stepping_and_emergency_stop(client):
    r = await client.post("/api/multimodal/sessions", json={"session_id": "api-live", "duration_s": 120,
                                                             "run_to_end": False, "mode": "feedback_research"})
    assert r.json()["controller_state"] == "CALIBRATION" and not r.json()["done"]
    st = (await client.post("/api/multimodal/sessions/api-live/step?n=10")).json()
    assert len(st["ticks"]) == 10
    await client.post("/api/multimodal/sessions/api-live/command", json={"action": "pause"})
    st = (await client.post("/api/multimodal/sessions/api-live/step")).json()
    assert st["status"]["controller_state"] == "PAUSED"
    stop = (await client.post("/api/multimodal/sessions/api-live/command", json={"action": "emergency_stop"})).json()
    assert stop["controller_state"] == "TERMINATED" and stop["done"]
    assert (await client.post("/api/multimodal/sessions/api-live/step")).json()["ticks"] == []


async def test_sessions_persist_and_recover_paused(client):
    import app.api.multimodal as mm

    r = await client.post("/api/multimodal/sessions", json={"session_id": "api-p", "duration_s": 120,
                                                             "run_to_end": False, "mode": "feedback_research"})
    assert r.status_code == 200
    await client.post("/api/multimodal/sessions/api-p/step?n=40")
    row = (await client.get("/api/multimodal/persisted/api-p")).json()
    assert row["status"] == "RUNNING" and row["last_tick"] == 40 and row["n_decisions"] == 40
    assert row["calibration_version"] == 1 and row["model_versions"]["estimator"]
    mm._sessions.clear()
    assert mm.mark_interrupted_on_startup() == ["api-p"]
    rec = (await client.post("/api/multimodal/sessions/api-p/recover")).json()
    assert rec["hash_chain_verified"] and rec["controller_state"] == "PAUSED" and rec["resumed_mode"] == "shadow"
    assert rec["original_mode"] == "feedback_research"
    st = (await client.post("/api/multimodal/sessions/api-p/step")).json()
    assert st["status"]["controller_state"] == "PAUSED" and not st["ticks"][0]["delivered"]
    await client.post("/api/multimodal/sessions/api-p/command", json={"action": "resume"})
    st = (await client.post("/api/multimodal/sessions/api-p/step?n=3")).json()
    assert st["status"]["controller_state"] in {"ACTIVE_SHADOW", "SAFE_FALLBACK"}
    assert not any(t["delivered"] and t["controller_state"] == "FEEDBACK_RESEARCH" for t in st["ticks"])
    done = (await client.post("/api/multimodal/sessions/api-p/recover"))
    assert done.status_code in (200, 409)


async def test_validation_and_not_found(client):
    assert (await client.post("/api/multimodal/sessions", json={"session_id": "../x"})).status_code == 422
    assert (await client.get("/api/multimodal/sessions/nope")).status_code == 404


async def test_protocols_and_checklist(client):
    assert set((await client.get("/api/multimodal/protocols")).json()) == set("ABCDEFG")
    r = (await client.post("/api/multimodal/protocols/E/run")).json()
    assert r["result"]["design_simulation"] and "not a human neuroscience finding" in r["scope"]
    chk = (await client.get("/api/multimodal/hardware-checklist")).json()
    assert chk["status"] == "NO HARDWARE VALIDATED"
    gating = [i for s in chk["sections"] for i in s["items"] if i.get("gating")]
    assert any("leakage" in i["check"].lower() for i in gating)


class TestProtocolRunners:
    def test_a_with_permutation(self):
        r = run_protocol_a(n_permutations=3)
        assert r["result"]["mean"] > 0.8 and r["source_kinds"] == ["SYNTHETIC"]

    def test_b_and_c(self):
        b = run_protocol_b()
        assert 0.5 < b["result"]["auc_loso"] < 1.0
        c = run_protocol_c()
        assert c["result"]["within_subject"]["mean"] >= c["result"]["loso"]["mean"]

    def test_design_simulation_controls_type1_error(self):
        oc = design_operating_characteristics(n_per_arm=20, effects=(0.0,), n_sims=300)
        assert 0.02 <= oc["results"]["effect_0.0"]["rejection_rate"] <= 0.09

    def test_causal_protocols_labeled_simulation(self):
        r = run_protocol_causal("F", true_effect=0.0)
        assert r["result"]["design_simulation"] and r["source_kinds"] == ["SYNTHETIC"]
        with pytest.raises(ValueError):
            run_protocol_causal("A")
