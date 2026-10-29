"""Contract tests for the canonical scientific ledger and claim registry."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.research.ledger import build_snapshot, render_markdown, repo_root, write_outputs

pytestmark = pytest.mark.core

REPO = repo_root()
SCHEMA_FILES = ("claim.schema.json", "ledger.schema.json", "result.schema.json")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _artifact(
    artifact_id: str = "a.canonical",
    *,
    authority: str = "canonical",
    status_path: str = "status",
    status_map: dict[str, str] | None = None,
    required_fields: list[str] | None = None,
    supersedes: list[str] | None = None,
    superseded_by: str | None = None,
    gate_id: str = "G1",
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "path": f"results/{artifact_id}.json",
        "gate_id": gate_id,
        "authority": authority,
        "status_path": status_path,
        "status_map": status_map or {"PASS": "PASS"},
        "required_fields": required_fields or ["code_sha"],
        "supersedes": supersedes or [],
        "superseded_by": superseded_by,
        "note": "fixture",
    }


def _claim(**overrides: Any) -> dict[str, Any]:
    claim = {
        "claim_id": "claim.test",
        "statement": "A fixture claim that is long enough to pass the schema.",
        "status": "VALIDATED",
        "ceiling": "L1_BEHAVIORAL_ASSISTED",
        "gate_refs": ["G1"],
        "evidence": ["a.canonical"],
        "n": 1,
        "effect": "fixture",
        "uncertainty": "fixture",
        "forbidden_interpretations": ["overclaim"],
        "last_reviewed": "2026-10-29",
    }
    claim.update(overrides)
    return claim


def _gate(**overrides: Any) -> dict[str, Any]:
    gate = {
        "gate_id": "G1",
        "name": "Fixture gate",
        "canonical_artifact": "a.canonical",
        "claim_ids": ["claim.test"],
        "note": "fixture",
    }
    gate.update(overrides)
    return gate


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    schemas = root / "science" / "schemas"
    schemas.mkdir(parents=True)
    for name in SCHEMA_FILES:
        shutil.copy(REPO / "science" / "schemas" / name, schemas / name)
    _write_json(root / "results" / "a.canonical.json", {"status": "PASS", "code_sha": "abc1234"})
    _write_yaml(root / "science" / "registry" / "artifacts.yaml", {"version": 1, "artifacts": [_artifact()]})
    _write_yaml(root / "science" / "registry" / "gates.yaml", {"version": 1, "gates": [_gate()]})
    _write_yaml(
        root / "science" / "registry" / "claims.yaml",
        {"version": 1, "operating_ceiling": "L1_BEHAVIORAL_ASSISTED", "claims": [_claim()]},
    )
    return root


def test_valid_fixture_passes(tmp_path: Path) -> None:
    snapshot = build_snapshot(_repo(tmp_path))
    assert snapshot["errors"] == []
    assert [gate["status"] for gate in snapshot["gates"]] == ["PASS"]
    assert [claim["status"] for claim in snapshot["claims"]] == ["VALIDATED"]


def test_missing_provenance_is_an_error(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write_json(root / "results" / "a.canonical.json", {"status": "PASS"})
    snapshot = build_snapshot(root)
    assert any("missing provenance fields" in error for error in snapshot["errors"])


def test_unmapped_status_is_an_error(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write_json(root / "results" / "a.canonical.json", {"status": "MAYBE", "code_sha": "abc1234"})
    snapshot = build_snapshot(root)
    assert any("unmapped status" in error for error in snapshot["errors"])


def test_duplicate_canonical_artifact_is_an_error(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write_json(root / "results" / "a.second.json", {"status": "PASS", "code_sha": "abc1234"})
    artifacts = [
        _artifact(),
        _artifact("a.second", required_fields=["code_sha"]),
    ]
    _write_yaml(root / "science" / "registry" / "artifacts.yaml", {"version": 1, "artifacts": artifacts})
    snapshot = build_snapshot(root)
    assert any("canonical artifacts" in error for error in snapshot["errors"])


def test_claim_cannot_outrun_evidence(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write_json(root / "results" / "a.canonical.json", {"status": "NULL", "code_sha": "abc1234"})
    _write_yaml(
        root / "science" / "registry" / "artifacts.yaml",
        {"version": 1, "artifacts": [_artifact(status_map={"NULL": "NULL"})]},
    )
    snapshot = build_snapshot(root)
    assert any("requires evidence" in error for error in snapshot["errors"])


def test_supersession_cycle_is_an_error(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    artifacts = [
        _artifact(),
        _artifact("a.old", authority="historical", superseded_by="a.new"),
        _artifact("a.new", authority="historical", superseded_by="a.old"),
    ]
    _write_json(root / "results" / "a.old.json", {"status": "PASS", "code_sha": "abc1234"})
    _write_json(root / "results" / "a.new.json", {"status": "PASS", "code_sha": "abc1234"})
    _write_yaml(root / "science" / "registry" / "artifacts.yaml", {"version": 1, "artifacts": artifacts})
    snapshot = build_snapshot(root)
    assert any("cycle" in error for error in snapshot["errors"])


def test_render_is_deterministic_and_keeps_boundaries(tmp_path: Path) -> None:
    snapshot = build_snapshot(_repo(tmp_path))
    first = render_markdown(snapshot)
    second = render_markdown(snapshot)
    assert first == second
    assert "What this document does not establish" in first
    assert "does not authorize human data collection" in first


def test_write_outputs(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    snapshot = build_snapshot(root)
    ledger_path, status_path = write_outputs(snapshot, root)
    assert ledger_path.is_file()
    assert status_path.is_file()
    written = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert written["gates"][0]["gate_id"] == "G1"


def test_real_registry_is_consistent() -> None:
    snapshot = build_snapshot(REPO)
    assert snapshot["errors"] == []
    statuses = {gate["gate_id"]: gate["status"] for gate in snapshot["gates"]}
    assert statuses["C1"] == "NULL"
    assert statuses["C3XAT_R1"] == "LIMITED"
    assert statuses["ANIMUS_P2"] == "BLOCKED"
    claims = {claim["claim_id"]: claim for claim in snapshot["claims"]}
    assert claims["claim.perception_neural_content"]["status"] == "PILOT"
    assert claims["claim.imagery_neural_content"]["status"] == "BLOCKED"
    assert claims["claim.clinical_or_diagnostic"]["status"] == "BLOCKED"


def test_generated_status_document_is_current() -> None:
    snapshot = build_snapshot(REPO)
    status_path = REPO / "docs" / "program" / "PROGRAM_STATUS.md"
    assert status_path.read_text(encoding="utf-8") == render_markdown(snapshot)
