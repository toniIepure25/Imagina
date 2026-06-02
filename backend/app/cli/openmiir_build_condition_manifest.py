"""OpenMIIR Condition Manifest Builder CLI v3.9.4.

Builds condition_manifest.json ONLY if confirmed semantic mappings exist.
With v3.9.4 MATLAB evidence, can produce enriched drafts with trigger semantics.
"""

import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
META_DIR = os.path.join(BASE, "..", "..", "data", "external", "openmiir", "meta")


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_build_condition_manifest")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--resolver-report", default=None)
    p.add_argument("--allow-hypotheses", type=str, default="false")
    p.add_argument("--min-confidence", default="confirmed",
                   choices=["confirmed", "strong_hypothesis", "weak_hypothesis"])
    return p


def _load_resolver(path=None):
    if path and os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    default = os.path.join(EXPORTS, "openmiir_semantic_event_resolver.json")
    if os.path.exists(default):
        with open(default) as f:
            return json.load(f)
    return None


def _build_draft_manifest(resolver, allow_hypotheses, min_confidence):
    families = resolver.get("event_code_families", {})
    trigger_semantics = resolver.get("trigger_semantics", {})
    condition_map = resolver.get("condition_code_map", {})
    strong = resolver.get("strong_hypothesis_mappings", {})

    conditions = []
    for fn, fd in families.items():
        tm = fd.get("trigger_mapping", {})
        cond_label = tm.get("condition", fd.get("structural_meaning", ""))
        conditions.append({
            "condition_id": fn,
            "event_codes": fd.get("codes", []),
            "condition_label": str(cond_label),
            "evidence_source": fd.get("evidence_source", ""),
            "confidence": "strong_hypothesis" if "matlab" in str(fd.get("evidence_source", ""))
                          else "weak_hypothesis",
        })

    draft = {
        "manifest_version": "draft_v3.9.4",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "is_production": False,
        "is_scientific_valid": False,
        "scientific_use_allowed": False,
        "reason": "semantic_mapping_unconfirmed",
        "semantic_mapping_confirmed": resolver.get("semantic_mapping_resolved", False),
        "trigger_semantics_confirmed": True,
        "trigger_semantics": trigger_semantics,
        "stimtracker_encoding_empirically_validated": resolver.get("empirical_mapping_validated", False),
        "stimtracker_encoding_confidence": resolver.get("stimtracker_encoding_confidence", "not_available"),
        "stimtracker_validation_score": (
            resolver.get("stimtracker_encoding_validation", {}).get("overall_score", 0)
            if resolver.get("stimtracker_encoding_validation") else None
        ),
        "production_unlock_allowed": False,
        "empirical_condition_code_map": resolver.get("empirical_condition_code_map", {}),
        "condition_code_map": condition_map,
        "event_code_families": families,
        "strong_hypothesis_mappings": strong,
        "conditions": conditions,
        "perception_codes": condition_map.get("perception_codes", []),
        "imagery_codes": condition_map.get("imagery_codes", []),
        "baseline_codes": condition_map.get("baseline_codes", []),
        "unresolved_event_codes": resolver.get("unresolved_codes", []),
        "warnings": [
            "DRAFT — Trigger semantics confirmed by MATLAB code: "
            "1=perception, 2=cued_imagery, 3=uncued_imagery, 4=noise.",
            "Two-digit stim codes ({stimulus_group}{trigger_type}) map to conditions via strong_hypothesis.",
            "Cedrus StimTracker encoding not explicitly documented. No production manifest.",
            "100-series vs 200-series distinction remains structural hypothesis.",
            "NOT valid for scientific claims about condition-level EEG analysis.",
        ],
        "allow_hypotheses": allow_hypotheses,
        "min_confidence": min_confidence,
        "next_steps": [
            "Confirm Cedrus StimTracker encoding format mapping ['mh',X,0] to stim channel codes",
            "Verify condition code map with stimulus metadata (Stimuli_Meta.xlsx)",
            "Contact sstober for StimTracker configuration documentation",
        ],
    }
    return draft


def main(argv=None):
    args = build_parser().parse_args(argv)
    allow = args.allow_hypotheses.lower() in ("true", "1", "yes")
    resolver = _load_resolver(args.resolver_report)

    if not resolver:
        print("No resolver report found.", file=sys.stderr)
        return 1

    resolved = resolver.get("semantic_mapping_resolved", False)
    confirmed = resolver.get("confirmed_mappings", {})

    if resolved and confirmed:
        manifest = {
            "manifest_version": "production_v3.9.4",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "is_production": True,
            "is_scientific_valid": True,
            "scientific_use_allowed": True,
            "semantic_mapping_confirmed": True,
            "conditions": [
                {
                    "condition_id": k,
                    "event_codes": v.get("codes", v.get("event_codes", [])),
                    "semantic_label": v.get("label", v.get("semantic_label", "")),
                    "confidence": "confirmed",
                }
                for k, v in confirmed.items()
            ],
        }
        output_path = os.path.join(META_DIR, "condition_manifest.json")
        with open(output_path, "w") as f:
            json.dump(manifest, f, indent=2, default=str)
        print(f"Production condition manifest: {output_path}", file=sys.stderr)
    else:
        draft = _build_draft_manifest(resolver, allow, args.min_confidence)
        output_path = os.path.join(EXPORTS, "openmiir_condition_manifest_draft.json")
        with open(output_path, "w") as f:
            json.dump(draft, f, indent=2, default=str)

        print(f"Draft manifest: {output_path}", file=sys.stderr)
        print("  Production: No (semantic mapping unresolved)", file=sys.stderr)
        print("  Trigger semantics: CONFIRMED (MATLAB)", file=sys.stderr)
        print(f"  Perception codes: {draft.get('perception_codes', [])}", file=sys.stderr)
        print(f"  Imagery codes: {draft.get('imagery_codes', [])}", file=sys.stderr)

        if not allow:
            print("  Exit code 1: --allow-hypotheses is false", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
