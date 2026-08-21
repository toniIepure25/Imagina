"""Authoritative NSD-Imagery beta-row block mapping for subj01.

Resolves the 720 raw beta-row vs. 576 behavioral-task-trial discrepancy per
docs/research/C3_NSDIMAGERY_ROW_MAPPING_AMENDMENT.md: vision and imagery
trials produce one beta each, attention trials produce two (cue epoch +
detection epoch), giving 3*48 + 6*48 + 3*48*2 = 720. Offsets below are
derived programmatically from the run order and per-run beta-multiplicity
spec, not hardcoded as a literal table.
"""
from __future__ import annotations

from dataclasses import dataclass

RUN_ORDER = [
    "visA", "attA", "imgA_1", "visB", "attB", "imgB_1",
    "visC", "attC", "imgC_1", "imgA_2", "imgB_2", "imgC_2",
]

TRIALS_PER_RUN = 48

# vision/imagery: 1 beta per trial. attention: 2 betas per trial (cue + detection).
BETA_MULTIPLICITY = {
    "vis": 1, "att": 2, "img": 1,
}


def _run_kind(run_name: str) -> str:
    if run_name.startswith("vis"):
        return "vis"
    if run_name.startswith("att"):
        return "att"
    if run_name.startswith("img"):
        return "img"
    raise ValueError(f"Unrecognized run name: {run_name}")


def _stimulus_set(run_name: str) -> str:
    # e.g. "visA" -> "A", "imgB_1" -> "B", "attC" -> "C"
    for letter in ("A", "B", "C"):
        if letter in run_name:
            return letter
    raise ValueError(f"Cannot determine stimulus set for run: {run_name}")


@dataclass(frozen=True)
class RunBlock:
    run_name: str
    run_number: int  # 1-based, per RUN_ORDER
    kind: str  # "vis", "att", "img"
    stimulus_set: str  # "A", "B", "C"
    n_trials: int
    n_betas: int
    row_start: int  # 0-based, inclusive
    row_end: int  # 0-based, exclusive


def compute_run_blocks() -> list[RunBlock]:
    """Derive the 0-based [start, end) beta-row span for each of the 12 runs
    from RUN_ORDER, TRIALS_PER_RUN, and BETA_MULTIPLICITY. Does not hardcode
    the resulting offsets.
    """
    blocks: list[RunBlock] = []
    cursor = 0
    for i, run_name in enumerate(RUN_ORDER, start=1):
        kind = _run_kind(run_name)
        mult = BETA_MULTIPLICITY[kind]
        n_betas = TRIALS_PER_RUN * mult
        blocks.append(RunBlock(
            run_name=run_name, run_number=i, kind=kind,
            stimulus_set=_stimulus_set(run_name), n_trials=TRIALS_PER_RUN,
            n_betas=n_betas, row_start=cursor, row_end=cursor + n_betas,
        ))
        cursor += n_betas
    return blocks


def total_expected_beta_rows() -> int:
    return sum(b.n_betas for b in compute_run_blocks())


def expected_counts() -> dict[str, int]:
    blocks = compute_run_blocks()
    vision_rows = sum(b.n_betas for b in blocks if b.kind == "vis")
    imagery_rows = sum(b.n_betas for b in blocks if b.kind == "img")
    attention_rows = sum(b.n_betas for b in blocks if b.kind == "att")
    return {
        "total": vision_rows + imagery_rows + attention_rows,
        "vision_rows": vision_rows,
        "imagery_rows": imagery_rows,
        "attention_rows": attention_rows,
        "vision_trials": sum(b.n_trials for b in blocks if b.kind == "vis"),
        "imagery_trials": sum(b.n_trials for b in blocks if b.kind == "img"),
        "attention_trials": sum(b.n_trials for b in blocks if b.kind == "att"),
    }


def block_for_row(row_index: int) -> RunBlock:
    for b in compute_run_blocks():
        if b.row_start <= row_index < b.row_end:
            return b
    raise IndexError(f"row_index {row_index} out of range [0, {total_expected_beta_rows()})")
