"""Canonical scientific ledger.

The ledger is the single machine-readable source of truth for two questions:

1. What is the canonical status of each research gate?
2. What may the project currently claim, and what is explicitly forbidden?

Gate status is never typed by hand into prose. It is derived from one canonical result artifact per
gate, with historical artifacts preserved and linked by explicit supersession. Claims reference
artifacts, so a claim cannot silently outrun its evidence.

Run ``python -m app.cli.science_ledger --check`` from ``backend/``. The command exits non-zero on a
missing artifact, an unmapped status, a duplicate canonical gate, a broken supersession link, or a
claim whose evidence cannot support its status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

GATE_STATUSES = frozenset(
    {
        "NOT_STARTED",
        "BLOCKED",
        "RUNNING",
        "PASS",
        "NULL",
        "FAIL",
        "LIMITED",
        "PILOT",
        "SUPERSEDED",
    }
)
CLAIM_STATUSES = frozenset(
    {
        "UNVALIDATED",
        "PILOT",
        "LIMITED",
        "VALIDATED",
        "REPLICATED",
        "DEPRECATED",
        "BLOCKED",
    }
)
AUTHORITIES = frozenset({"canonical", "historical", "supporting"})
OPERATING_CEILING = "L1_BEHAVIORAL_ASSISTED"

_CLAIM_EVIDENCE_REQUIREMENTS: dict[str, frozenset[str]] = {
    "VALIDATED": frozenset({"PASS", "VALIDATED", "REPLICATED"}),
    "REPLICATED": frozenset({"REPLICATED"}),
    "LIMITED": frozenset({"PASS", "LIMITED", "VALIDATED", "REPLICATED"}),
    "PILOT": frozenset({"PILOT", "LIMITED", "PASS", "VALIDATED", "REPLICATED"}),
}

_MISSING = object()


class LedgerError(RuntimeError):
    """A registry or artifact violates the ledger contract."""


@dataclass(frozen=True)
class ArtifactSpec:
    artifact_id: str
    path: str
    gate_id: str
    authority: str
    status_path: str
    status_map: dict[str, str]
    required_fields: tuple[str, ...] = ()
    supersedes: tuple[str, ...] = ()
    superseded_by: str | None = None
    note: str | None = None

    @classmethod
    def from_mapping(cls, raw: Any, where: str) -> ArtifactSpec:
        if not isinstance(raw, dict):
            raise LedgerError(f"{where}: artifact entry must be a mapping")
        required = ("artifact_id", "path", "gate_id", "authority", "status_path", "status_map")
        missing = [key for key in required if key not in raw]
        if missing:
            raise LedgerError(f"{where}: missing keys {missing}")
        authority = raw["authority"]
        if authority not in AUTHORITIES:
            raise LedgerError(f"{where}: unknown authority {authority!r}")
        status_map = raw["status_map"]
        if not isinstance(status_map, dict) or not status_map:
            raise LedgerError(f"{where}: status_map must be a non-empty mapping")
        for raw_status, canonical in status_map.items():
            if not isinstance(raw_status, str) or not isinstance(canonical, str):
                raise LedgerError(f"{where}: status_map keys and values must be strings")
            if canonical not in GATE_STATUSES:
                raise LedgerError(f"{where}: status_map target {canonical!r} is not a gate status")
        supersedes = raw.get("supersedes", [])
        required_fields = raw.get("required_fields", [])
        if not isinstance(supersedes, list) or not all(isinstance(item, str) for item in supersedes):
            raise LedgerError(f"{where}: supersedes must be a list of artifact ids")
        if not isinstance(required_fields, list) or not all(isinstance(item, str) for item in required_fields):
            raise LedgerError(f"{where}: required_fields must be a list of dotted paths")
        return cls(
            artifact_id=raw["artifact_id"],
            path=raw["path"],
            gate_id=raw["gate_id"],
            authority=authority,
            status_path=raw["status_path"],
            status_map=dict(status_map),
            required_fields=tuple(required_fields),
            supersedes=tuple(supersedes),
            superseded_by=raw.get("superseded_by"),
            note=raw.get("note"),
        )


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    path: str
    gate_id: str
    authority: str
    raw_status: str
    status: str
    sha256: str
    size_bytes: int
    superseded_by: str | None
    note: str | None = None


def repo_root() -> Path:
    """Return the repository root from ``backend/app/research/ledger.py``."""
    return Path(__file__).resolve().parents[3]


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise LedgerError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise LedgerError(f"invalid JSON in {path}: {exc}") from exc


def _load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise LedgerError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise LedgerError(f"invalid YAML in {path}: {exc}") from exc


def _get(payload: Any, dotted: str) -> Any:
    current = payload
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _is_blank(value: Any) -> bool:
    return value is _MISSING or value is None or value == ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_artifacts(root: Path) -> dict[str, ArtifactSpec]:
    doc = _load_yaml(root / "science" / "registry" / "artifacts.yaml")
    if not isinstance(doc, dict) or not isinstance(doc.get("artifacts"), list):
        raise LedgerError("science/registry/artifacts.yaml must contain an artifacts list")
    specs: dict[str, ArtifactSpec] = {}
    for index, raw in enumerate(doc["artifacts"]):
        spec = ArtifactSpec.from_mapping(raw, f"artifacts[{index}]")
        if spec.artifact_id in specs:
            raise LedgerError(f"duplicate artifact_id {spec.artifact_id!r}")
        specs[spec.artifact_id] = spec
    if not specs:
        raise LedgerError("artifacts registry is empty")
    return specs


def _load_gates(root: Path) -> list[dict[str, Any]]:
    doc = _load_yaml(root / "science" / "registry" / "gates.yaml")
    if not isinstance(doc, dict) or not isinstance(doc.get("gates"), list):
        raise LedgerError("science/registry/gates.yaml must contain a gates list")
    gates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(doc["gates"]):
        if not isinstance(raw, dict):
            raise LedgerError(f"gates[{index}]: gate entry must be a mapping")
        for key in ("gate_id", "name", "canonical_artifact"):
            if not raw.get(key):
                raise LedgerError(f"gates[{index}]: missing {key}")
        if raw["gate_id"] in seen:
            raise LedgerError(f"duplicate gate_id {raw['gate_id']!r}")
        seen.add(raw["gate_id"])
        gates.append(raw)
    return gates


def _load_claims(root: Path) -> dict[str, Any]:
    doc = _load_yaml(root / "science" / "registry" / "claims.yaml")
    if not isinstance(doc, dict) or not isinstance(doc.get("claims"), list):
        raise LedgerError("science/registry/claims.yaml must contain a claims list")
    if doc.get("operating_ceiling") != OPERATING_CEILING:
        raise LedgerError(f"operating_ceiling must be {OPERATING_CEILING!r}")
    schema = _read_json(root / "science" / "schemas" / "claim.schema.json")
    validator = Draft202012Validator(schema)
    seen: set[str] = set()
    for index, claim in enumerate(doc["claims"]):
        errors = sorted(validator.iter_errors(claim), key=lambda error: list(error.path))
        if errors:
            detail = "; ".join(error.message for error in errors)
            raise LedgerError(f"claims[{index}] ({claim.get('claim_id')!r}) is invalid: {detail}")
        claim_id = claim["claim_id"]
        if claim_id in seen:
            raise LedgerError(f"duplicate claim_id {claim_id!r}")
        seen.add(claim_id)
    return doc


def _load_records(root: Path, specs: dict[str, ArtifactSpec], errors: list[str]) -> dict[str, ArtifactRecord]:
    records: dict[str, ArtifactRecord] = {}
    for artifact_id in sorted(specs):
        spec = specs[artifact_id]
        artifact_path = root / spec.path
        if not artifact_path.is_file():
            errors.append(f"{artifact_id}: missing artifact {spec.path}")
            continue
        try:
            payload = _read_json(artifact_path)
        except LedgerError as exc:
            errors.append(f"{artifact_id}: {exc}")
            continue
        raw_status = _get(payload, spec.status_path)
        if raw_status is _MISSING:
            errors.append(f"{artifact_id}: status_path {spec.status_path!r} not found in {spec.path}")
            continue
        if not isinstance(raw_status, str):
            errors.append(f"{artifact_id}: status at {spec.status_path!r} is not a string")
            continue
        mapped_status = spec.status_map.get(raw_status)
        if mapped_status is None:
            errors.append(
                f"{artifact_id}: unmapped status {raw_status!r}; "
                f"add it to status_map with an explicit canonical meaning"
            )
            continue
        missing_fields = [field for field in spec.required_fields if _is_blank(_get(payload, field))]
        if missing_fields:
            errors.append(f"{artifact_id}: missing provenance fields {missing_fields}")
        records[artifact_id] = ArtifactRecord(
            artifact_id=artifact_id,
            path=spec.path,
            gate_id=spec.gate_id,
            authority=spec.authority,
            raw_status=raw_status,
            status=mapped_status,
            sha256=_sha256(artifact_path),
            size_bytes=artifact_path.stat().st_size,
            superseded_by=spec.superseded_by,
            note=spec.note,
        )
    return records


def _check_supersession(
    specs: dict[str, ArtifactSpec],
    records: dict[str, ArtifactRecord],
    errors: list[str],
    warnings: list[str],
) -> None:
    graph: dict[str, list[str]] = {artifact_id: [] for artifact_id in specs}
    for artifact_id, spec in specs.items():
        if spec.superseded_by is not None:
            if spec.superseded_by not in specs:
                errors.append(f"{artifact_id}: superseded_by unknown artifact {spec.superseded_by!r}")
            elif spec.authority == "canonical":
                errors.append(f"{artifact_id}: canonical artifact cannot be superseded")
            else:
                graph[spec.superseded_by].append(artifact_id)
        for older in spec.supersedes:
            if older not in specs:
                errors.append(f"{artifact_id}: supersedes unknown artifact {older!r}")
            elif older == artifact_id:
                errors.append(f"{artifact_id}: cannot supersede itself")
            else:
                graph[artifact_id].append(older)
        if spec.authority == "historical" and spec.superseded_by is None:
            warnings.append(f"{artifact_id}: historical artifact has no superseded_by link")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            errors.append(f"supersession cycle includes {node!r}")
            return
        if node in visited:
            return
        visiting.add(node)
        for child in graph.get(node, []):
            visit(child)
        visiting.discard(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node)

    for artifact_id, spec in specs.items():
        if spec.superseded_by and spec.superseded_by in specs:
            newer = specs[spec.superseded_by]
            if artifact_id not in newer.supersedes:
                warnings.append(
                    f"{artifact_id}: superseded_by {spec.superseded_by!r}, "
                    f"but that artifact does not list it in supersedes"
                )
        if artifact_id not in records:
            continue
        for older in spec.supersedes:
            older_spec = specs.get(older)
            if older_spec and older_spec.superseded_by not in (None, artifact_id):
                warnings.append(
                    f"{artifact_id}: supersedes {older!r}, but {older!r} points to "
                    f"{older_spec.superseded_by!r}"
                )


def _check_gates(
    root: Path,
    gates: list[dict[str, Any]],
    specs: dict[str, ArtifactSpec],
    records: dict[str, ArtifactRecord],
    errors: list[str],
) -> list[dict[str, Any]]:
    del root
    resolved: list[dict[str, Any]] = []
    for gate in gates:
        gate_id = gate["gate_id"]
        canonical_id = gate["canonical_artifact"]
        spec = specs.get(canonical_id)
        if spec is None:
            errors.append(f"{gate_id}: canonical artifact {canonical_id!r} is not registered")
            continue
        if spec.gate_id != gate_id:
            errors.append(f"{gate_id}: canonical artifact {canonical_id!r} belongs to {spec.gate_id!r}")
        if spec.authority != "canonical":
            errors.append(f"{gate_id}: canonical artifact {canonical_id!r} has authority {spec.authority!r}")
        record = records.get(canonical_id)
        if record is None:
            errors.append(f"{gate_id}: canonical artifact {canonical_id!r} could not be loaded")
            continue
        resolved.append(
            {
                "gate_id": gate_id,
                "name": gate["name"],
                "status": record.status,
                "canonical_artifact": canonical_id,
                "claims": list(gate.get("claim_ids", [])),
                "note": gate.get("note"),
            }
        )

    for gate_id in {spec.gate_id for spec in specs.values()}:
        if gate_id not in {gate["gate_id"] for gate in gates}:
            errors.append(f"{gate_id}: artifact gate has no entry in gates.yaml")

    for gate_id in {gate["gate_id"] for gate in gates}:
        canonical = [
            record
            for record in records.values()
            if record.gate_id == gate_id and record.authority == "canonical"
        ]
        if len(canonical) > 1:
            errors.append(
                f"{gate_id}: {len(canonical)} canonical artifacts "
                f"({', '.join(sorted(record.artifact_id for record in canonical))}); exactly one is allowed"
            )
    return resolved


def _check_claims(
    root: Path,
    claim_doc: dict[str, Any],
    gates: list[dict[str, Any]],
    records: dict[str, ArtifactRecord],
    errors: list[str],
) -> list[dict[str, Any]]:
    del root
    gates_by_id = {gate["gate_id"]: gate for gate in gates}
    resolved: list[dict[str, Any]] = []
    for claim in claim_doc["claims"]:
        claim_id = claim["claim_id"]
        gate_refs = claim.get("gate_refs", [])
        evidence = claim.get("evidence", [])
        for gate_id in gate_refs:
            if gate_id not in gates_by_id:
                errors.append(f"{claim_id}: unknown gate_ref {gate_id!r}")
            elif claim_id not in gates_by_id[gate_id].get("claim_ids", []):
                errors.append(f"{claim_id}: gate {gate_id!r} does not list this claim in claim_ids")
        for gate_id, gate in gates_by_id.items():
            if claim_id in gate.get("claim_ids", []) and gate_id not in gate_refs:
                errors.append(f"{claim_id}: listed on gate {gate_id!r} but missing from gate_refs")
        evidence_statuses: list[str] = []
        for artifact_id in evidence:
            record = records.get(artifact_id)
            if record is None:
                errors.append(f"{claim_id}: unknown evidence artifact {artifact_id!r}")
                continue
            evidence_statuses.append(record.status)
        required = _CLAIM_EVIDENCE_REQUIREMENTS.get(claim["status"])
        if required is not None and not (set(evidence_statuses) & required):
            errors.append(
                f"{claim_id}: status {claim['status']!r} requires evidence in {sorted(required)}, "
                f"but evidence statuses are {sorted(set(evidence_statuses)) or 'none'}"
            )
        if claim["status"] in {"VALIDATED", "REPLICATED"} and claim["ceiling"] != OPERATING_CEILING:
            errors.append(
                f"{claim_id}: {claim['status']} at ceiling {claim['ceiling']!r} exceeds the operating "
                f"ceiling {OPERATING_CEILING!r}"
            )
        resolved.append(
            {
                "claim_id": claim_id,
                "statement": claim["statement"],
                "status": claim["status"],
                "ceiling": claim["ceiling"],
                "gate_refs": list(gate_refs),
                "evidence": list(evidence),
                "n": claim.get("n"),
                "effect": claim.get("effect"),
                "uncertainty": claim.get("uncertainty"),
            }
        )
    return resolved


def build_snapshot(root: Path | None = None) -> dict[str, Any]:
    """Build and validate the ledger snapshot. Errors are returned, not raised."""
    root = (root or repo_root()).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    specs = _load_artifacts(root)
    gates_raw = _load_gates(root)
    claim_doc = _load_claims(root)
    records = _load_records(root, specs, errors)
    _check_supersession(specs, records, errors, warnings)
    gates = _check_gates(root, gates_raw, specs, records, errors)
    claims = _check_claims(root, claim_doc, gates_raw, records, errors)
    artifacts = [
        {
            "artifact_id": record.artifact_id,
            "path": record.path,
            "gate_id": record.gate_id,
            "authority": record.authority,
            "raw_status": record.raw_status,
            "status": record.status,
            "superseded_by": record.superseded_by,
            "sha256": record.sha256,
            "bytes": record.size_bytes,
            "note": record.note,
        }
        for record in sorted(records.values(), key=lambda item: item.artifact_id)
    ]
    snapshot: dict[str, Any] = {
        "schema_version": "1.0",
        "generated_from": "science/registry",
        "operating_ceiling": claim_doc.get("operating_ceiling"),
        "reviewed_at": claim_doc.get("reviewed_at"),
        "gates": gates,
        "claims": claims,
        "artifacts": artifacts,
        "errors": errors,
        "warnings": warnings,
    }
    ledger_schema = _read_json(root / "science" / "schemas" / "ledger.schema.json")
    validator = Draft202012Validator(ledger_schema)
    schema_errors = sorted(validator.iter_errors(snapshot), key=lambda error: list(error.path))
    if schema_errors:
        raise LedgerError(
            "generated snapshot violates ledger.schema.json: "
            + "; ".join(error.message for error in schema_errors)
        )
    return snapshot


def _cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(snapshot: dict[str, Any]) -> str:
    """Render a deterministic status document from a snapshot."""
    lines = [
        "# IMAGINA Program Status",
        "",
        "> Generated from `science/registry/` by `python -m app.cli.science_ledger --write`.",
        "> Do not edit by hand. Change the registry or the result artifact instead.",
        "",
        f"**Operating ceiling:** `{snapshot.get('operating_ceiling')}`  ",
        f"**Registry reviewed:** {snapshot.get('reviewed_at') or 'unspecified'}",
        "",
        "## Gates",
        "",
        "| Gate | Name | Status | Canonical artifact | Note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for gate in snapshot["gates"]:
        lines.append(
            f"| {_cell(gate['gate_id'])} | {_cell(gate['name'])} | `{_cell(gate['status'])}` | "
            f"`{_cell(gate['canonical_artifact'])}` | {_cell(gate.get('note'))} |"
        )
    lines += [
        "",
        "## Claims",
        "",
        "| Claim | Status | Ceiling | n | Evidence | Statement |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for claim in snapshot["claims"]:
        evidence = ", ".join(f"`{item}`" for item in claim["evidence"]) or "none"
        n = "" if claim.get("n") is None else str(claim["n"])
        lines.append(
            f"| `{_cell(claim['claim_id'])}` | `{_cell(claim['status'])}` | `{_cell(claim['ceiling'])}` | "
            f"{_cell(n)} | {evidence} | {_cell(claim['statement'])} |"
        )
    lines += [
        "",
        "## Supersession and conflicts",
        "",
    ]
    superseded = [item for item in snapshot["artifacts"] if item.get("superseded_by")]
    if superseded:
        for item in superseded:
            lines.append(
                f"- `{item['artifact_id']}` (`{item['raw_status']}` -> `{item['status']}`) "
                f"is superseded by `{item['superseded_by']}`."
            )
    else:
        lines.append("- No superseded artifacts are registered.")
    if snapshot["errors"]:
        lines += ["", "### Errors", ""]
        lines.extend(f"- {error}" for error in snapshot["errors"])
    if snapshot["warnings"]:
        lines += ["", "### Warnings", ""]
        lines.extend(f"- {warning}" for warning in snapshot["warnings"])
    lines += [
        "",
        "## Provenance",
        "",
        "| Artifact | Gate | Authority | Mapped status | SHA-256 | Bytes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in snapshot["artifacts"]:
        lines.append(
            f"| `{_cell(item['artifact_id'])}` | {_cell(item['gate_id'])} | {_cell(item['authority'])} | "
            f"`{_cell(item['status'])}` | `{_cell(item['sha256'])}` | {item['bytes']} |"
        )
    lines += [
        "",
        "## What this document does not establish",
        "",
        "- It does not validate a claim; it records the current evidence and the claim boundary.",
        "- It does not authorize human data collection, clinical use, or a new acquisition.",
        "- It does not resolve a paused or blocked confirmatory analysis by prose.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(snapshot: dict[str, Any], root: Path | None = None) -> tuple[Path, Path]:
    """Write the generated ledger JSON and markdown status document."""
    root = (root or repo_root()).resolve()
    ledger_path = root / "results" / "ledger.json"
    status_path = root / "docs" / "program" / "PROGRAM_STATUS.md"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    status_path.write_text(render_markdown(snapshot), encoding="utf-8")
    return ledger_path, status_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and render the IMAGINA scientific ledger.")
    parser.add_argument("--root", type=Path, default=None, help="Repository root (default: auto-detect)")
    parser.add_argument("--check", action="store_true", help="Validate only (default)")
    parser.add_argument("--write", action="store_true", help="Write results/ledger.json and PROGRAM_STATUS.md")
    parser.add_argument("--json", action="store_true", help="Print the snapshot as JSON")
    args = parser.parse_args(argv)

    try:
        snapshot = build_snapshot(args.root)
    except LedgerError as exc:
        print(f"LEDGER ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    else:
        gates = " ".join(f"{gate['gate_id']}={gate['status']}" for gate in snapshot["gates"])
        print(f"ledger: {len(snapshot['artifacts'])} artifacts, {len(snapshot['gates'])} gates, "
              f"{len(snapshot['claims'])} claims")
        print(f"gates: {gates}")
        for warning in snapshot["warnings"]:
            print(f"WARNING: {warning}")
        for error in snapshot["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)

    if args.write:
        if snapshot["errors"]:
            print("refusing to write generated documents while ledger errors exist", file=sys.stderr)
            return 1
        ledger_path, status_path = write_outputs(snapshot, args.root)
        print(f"wrote {ledger_path}")
        print(f"wrote {status_path}")

    return 1 if snapshot["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
