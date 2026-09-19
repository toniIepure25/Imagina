"""ANIMUS-P2 subject PASS + dataset-level scientific gate.

Subject PASS (perception content decoding) requires ALL of: data/unit contract PASS, atlas QC PASS, content
margin M>0, within-test permutation p<0.01, identity-bootstrap CI lower>0, and positive margin under every
sealed seed. 2AFC/retrieval are supporting endpoints. The dataset gate uses a FIXED eligible denominator
(no shrinkage by decoding performance).
"""
from __future__ import annotations

import math


def subject_pass(result: dict) -> bool:
    return bool(
        result.get("data_contract_pass")
        and result.get("atlas_qc_pass")
        and result.get("margin_M", -1) > 0
        and result.get("permutation_p", 1) < 0.01
        and result.get("bootstrap_ci_lower", -1) > 0
        and result.get("all_seeds_positive"))


def required_passes(n_eligible: int) -> int:
    return max(2, math.ceil(n_eligible / 3))


def dataset_gate(n_pass: int, n_valid: int, n_eligible: int) -> str:
    if n_valid < n_eligible:
        return "ANIMUS_P2_BLOCKED_INCOMPLETE_MEASUREMENT"
    req = required_passes(n_eligible)
    if n_pass >= req:
        return "ANIMUS_P2_PERCEPTION_DECODER_VALIDATED"
    if n_pass > 0:
        return "ANIMUS_P2_PERCEPTION_DECODER_LIMITED"
    return "ANIMUS_P2_PERCEPTION_DECODER_FAIL"
