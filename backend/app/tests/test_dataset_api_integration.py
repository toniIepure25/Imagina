"""FastAPI integration tests for dataset endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

FORBIDDEN = ("samples", "raw_samples", "eeg_samples", "timeseries", "time_series", "eeg_window", "sample_array")


def _assert_no_raw_keys(data, path="root"):
    if isinstance(data, dict):
        for k, v in data.items():
            assert k not in FORBIDDEN, f"Forbidden key '{k}' at {path}"
            _assert_no_raw_keys(v, f"{path}.{k}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            _assert_no_raw_keys(item, f"{path}[{i}]")


def test_catalog_returns_200():
    r = client.get("/api/datasets/catalog")
    assert r.status_code == 200
    data = r.json()
    ids = {d["dataset_id"] for d in data}
    assert "fixture" in ids


def test_catalog_no_raw_keys():
    r = client.get("/api/datasets/catalog")
    _assert_no_raw_keys(r.json())


def test_fixture_readiness():
    r = client.get("/api/datasets/fixture/readiness")
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "fixture_demo"
    assert data["evaluation_ready"] is True


def test_openmiir_readiness_is_real_ready():
    r = client.get("/api/datasets/openmiir/readiness")
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "real_dataset_ready"


def test_fixture_manifest():
    r = client.get("/api/datasets/fixture/manifest")
    assert r.status_code == 200


def test_latest_eval_missing():
    r = client.get("/api/datasets/fixture/latest-eval")
    assert r.status_code == 200
    assert r.json()["eval_exists"] is False


def test_latest_eval_no_raw_keys():
    r = client.get("/api/datasets/fixture/latest-eval")
    _assert_no_raw_keys(r.json())


def test_unknown_dataset_readiness():
    r = client.get("/api/datasets/nonexistent/readiness")
    assert r.status_code == 200


def test_all_endpoints_no_server_error():
    for path in (
        "/api/datasets/catalog",
        "/api/datasets/fixture/manifest",
        "/api/datasets/fixture/readiness",
        "/api/datasets/openmiir/readiness",
        "/api/datasets/fixture/latest-eval",
    ):
        assert client.get(path).status_code == 200, f"Failed: {path}"
