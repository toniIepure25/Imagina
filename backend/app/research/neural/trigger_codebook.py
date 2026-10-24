"""Authoritative ds005815 (YOTO) trigger-code decode.

The dataset's own BIDS `events.tsv` files store only an opaque integer
`value` (trigger code) alongside a generic `trial_type` of `TrialProc`,
`BlockProc`, or `startIntro` — none of which are self-documenting (see
`docs/research/C1_DATASET_CANDIDATES.md`, "event_metadata_quality").

This table is transcribed verbatim from the dataset authors' own analysis
code, `trigger_info` in
`python/Event-Related Potential (ERP) Analysis/config.py` at
https://github.com/CECNL/YOTO_You_Only_Think_Once (fetched and cross-checked
against a real downloaded recording, sub-01/ses-1/task, during Commit 2
ingestion: the per-trigger-code occurrence counts observed in
`sub-01_ses-1_task-task_events.tsv` — {21: 12, 22: 12, 23: 24, 24-35: 8 each,
36-47: 4 each} — match exactly across both sources). This is the primary
source for trigger semantics; nothing here is inferred or guessed.

Every stimulus trigger code corresponds to two analyzable phases within the
same physical trial: a perception phase (stimulus presentation, ~2s) and an
imagery phase (mental visualization of the same stimulus, ~4s), each
recorded under the same trigger code in the raw event stream and
disambiguated here by phase, not by a separate code.
"""
from __future__ import annotations

from dataclasses import dataclass

# code -> descriptive tags, transcribed verbatim from the authors' config.py.
TRIGGER_INFO: dict[int, tuple[str, ...]] = {
    3: ("resting", "close"),
    5: ("resting", "open"),
    6: ("fixation",),
    21: ("visual", "face", "male"),
    22: ("visual", "face", "female"),
    23: ("visual", "square"),
    24: ("auditory", "speech", "a"),
    25: ("auditory", "speech", "o"),
    26: ("auditory", "speech", "i"),
    27: ("auditory", "music", "C"),
    28: ("auditory", "music", "D"),
    29: ("auditory", "music", "E"),
    30: ("mix", "visual", "auditory", "square", "speech", "a"),
    31: ("mix", "visual", "auditory", "square", "speech", "o"),
    32: ("mix", "visual", "auditory", "square", "speech", "i"),
    33: ("mix", "visual", "auditory", "square", "music", "C"),
    34: ("mix", "visual", "auditory", "square", "music", "D"),
    35: ("mix", "visual", "auditory", "square", "music", "E"),
    36: ("mix", "visual", "auditory", "face", "male", "speech", "a"),
    37: ("mix", "visual", "auditory", "face", "male", "speech", "o"),
    38: ("mix", "visual", "auditory", "face", "male", "speech", "i"),
    39: ("mix", "visual", "auditory", "face", "female", "speech", "a"),
    40: ("mix", "visual", "auditory", "face", "female", "speech", "o"),
    41: ("mix", "visual", "auditory", "face", "female", "speech", "i"),
    42: ("mix", "visual", "auditory", "face", "male", "music", "C"),
    43: ("mix", "visual", "auditory", "face", "male", "music", "D"),
    44: ("mix", "visual", "auditory", "face", "male", "music", "E"),
    45: ("mix", "visual", "auditory", "face", "female", "music", "C"),
    46: ("mix", "visual", "auditory", "face", "female", "music", "D"),
    47: ("mix", "visual", "auditory", "face", "female", "music", "E"),
}

# Non-trial marker codes: not stimuli, never produce a NeuralTrialManifest row.
NON_TRIAL_CODES = frozenset({3, 5, 6})

# Trigger codes whose stimulus tags include "visual" — the primary-imagery
# subset this project's visual-imagery scope actually analyzes (H2/H3).
VISUAL_CODES = frozenset(
    code for code, tags in TRIGGER_INFO.items()
    if "visual" in tags and code not in NON_TRIAL_CODES
)

# Trial-phase timing, transcribed from the paper's methods text (verified in
# Phase 0, `C1_DATASET_CANDIDATES.md`): fixation (2s) -> stimulus/perception
# (2s) -> imagery (4s) -> self-report (variable, not modeled as a fixed
# window). Onsets are relative to the single per-trial trigger event, which
# marks stimulus onset (the start of the perception phase).
PERCEPTION_PHASE_OFFSET_S = 0.0
PERCEPTION_PHASE_DURATION_S = 2.0
IMAGERY_PHASE_OFFSET_S = 2.0
IMAGERY_PHASE_DURATION_S = 4.0


@dataclass(frozen=True)
class TriggerMeaning:
    code: int
    modality: str  # "visual" | "auditory" | "mix"
    stimulus_id: str  # canonical descriptive identity, e.g. "visual_face_male"
    tags: tuple[str, ...]


def decode_trigger(code: int) -> TriggerMeaning | None:
    """Decode a raw ds005815 trigger code. Returns None for non-trial codes
    (resting/fixation markers) or any code absent from the verified table —
    callers must treat an unresolved code as a structured exclusion, never
    silently guess a condition."""
    if code in NON_TRIAL_CODES or code not in TRIGGER_INFO:
        return None
    tags = TRIGGER_INFO[code]
    if "mix" in tags:
        modality = "mix"
    elif "visual" in tags:
        modality = "visual"
    elif "auditory" in tags:
        modality = "auditory"
    else:
        return None
    stimulus_id = "_".join(tags)
    return TriggerMeaning(code=code, modality=modality, stimulus_id=stimulus_id, tags=tags)
