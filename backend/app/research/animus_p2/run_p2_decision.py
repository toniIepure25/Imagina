"""ANIMUS-P2 scientific decision + capability update.

Produces results/animus_p2/ANIMUS_P2_SCIENTIFIC_DECISION.json from the confirmatory per-subject results
(results/animus_p2/subjects/*.json) if they exist, else records the honest pre-confirmatory state
(protocol sealed; confirmatory pending cluster execution -> PERCEPTION_NEURAL_CONTENT NOT_VALIDATED). The
capability matrix is updated from the decision — validating perception NEVER raises imagery/dream/
reconstruction. Also emits the capability snapshot the product consults.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys

from app.core.animus.p2 import gate
from app.core.animus.p2.capability import (
    IMAGERY_NEURAL_CONTENT,
    PERCEPTION_NEURAL_CONTENT,
    ScientificCapabilityAuthorization,
    imagery_unauthorized_invariant,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "results", "animus_p2")
SUBJ_DIR = os.path.join(OUT, "subjects")


def _sh(o):
    o = dict(o)
    o.pop("self_hash", None)
    o["self_hash"] = hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
    return o


def load_confirmatory_subjects() -> list[dict]:
    return [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(os.path.join(SUBJ_DIR, "*.json")))]


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    subjects = load_confirmatory_subjects()
    seal_exists = os.path.exists(os.path.join(OUT, "animus_p2_protocol_seal.json"))

    if not subjects:
        decision = "ANIMUS_P2_BLOCKED_CONFIRMATORY_PENDING"
        reason = ("Prospective protocol sealed and method/bridge validated on synthetic data; the REAL "
                  "confirmatory perception decode (independent dataset on the OrchestrAIQ cluster) has not "
                  "produced per-subject results yet. No neural-content claim is made. Re-run this after the "
                  "confirmatory cluster job writes results/animus_p2/subjects/*.json.")
        n_pass = n_valid = n_eligible = 0
    else:
        n_eligible = len(subjects)
        n_valid = sum(1 for s in subjects if s.get("atlas_qc_pass") and s.get("data_contract_pass"))
        n_pass = sum(1 for s in subjects if s.get("pass"))
        decision = gate.dataset_gate(n_pass, n_valid, n_eligible)
        reason = f"confirmatory over {n_eligible} eligible subjects; {n_pass} passed the frozen subject gate"

    auth = ScientificCapabilityAuthorization().validate_perception(decision)
    assert imagery_unauthorized_invariant(auth), "invariant violated: imagery must stay unauthorized"

    out = {
        "artifact": "ANIMUS_P2_SCIENTIFIC_DECISION", "milestone": "ANIMUS-P2",
        "scientific_parent": "a0b6ca7", "protocol_sealed": seal_exists,
        "decision": decision, "reason": reason,
        "n_eligible": n_eligible, "n_valid": n_valid, "n_pass": n_pass,
        "required_passes": gate.required_passes(n_eligible) if n_eligible else None,
        "capability_after": auth.to_dict(),
        "perception_status": auth.status(PERCEPTION_NEURAL_CONTENT),
        "imagery_status": auth.status(IMAGERY_NEURAL_CONTENT),
        "imagery_remains_unauthorized": imagery_unauthorized_invariant(auth),
        "authorized_claim": ("Experimental validated perception-content neural adapter (visual perception "
                             "only)" if decision.endswith("VALIDATED") else "none (perception not validated)"),
        "forbidden_claims": ["imagery neural content", "thought decoding", "dream decoding",
                             "mental image reconstruction"],
    }
    json.dump(_sh(out), open(os.path.join(OUT, "ANIMUS_P2_SCIENTIFIC_DECISION.json"), "w"), indent=2)
    json.dump(_sh({"artifact": "ANIMUS_P2_CAPABILITY_SNAPSHOT", **auth.to_dict()}),
              open(os.path.join(OUT, "capability_snapshot.json"), "w"), indent=2)
    print("DECISION:", decision)
    print("perception:", out["perception_status"], "| imagery:", out["imagery_status"],
          "| imagery_unauthorized:", out["imagery_remains_unauthorized"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
