from __future__ import annotations

from app.schemas.research import InstrumentInfo

_INSTRUMENTS: dict[str, InstrumentInfo] = {
    "vviq2": InstrumentInfo(
        instrument_id="vviq2",
        name="Vividness of Visual Imagery Questionnaire 2",
        version="VVIQ-2 (Marks, 1995)",
        citation="Marks, D.F. (1995). New directions for mental imagery research. Journal of Mental Imagery, 19(3-4), 153-167.",
        license_status="published_scale_no_redistribution_restriction_known",
        scoring_direction="higher_is_more_vivid",
        items_included=False,
        acquisition_instructions="Administer the 16-item VVIQ-2 on paper or via a separate form. Score items 1-5 (1=perfectly vivid, 5=no image). Reverse-score so higher = more vivid. Sum all 16 items. Range: 16-80.",
    ),
    "perceived_contingency": InstrumentInfo(
        instrument_id="perceived_contingency",
        name="Perceived Contingency Rating",
        version="1.0",
        citation="Study-specific single-item measure.",
        license_status="study_specific_no_license_required",
        scoring_direction="higher_is_more_contingent",
        items_included=True,
        acquisition_instructions="Single item: 'To what extent did you feel the visual feedback responded to your mental imagery?' rated 1 (not at all) to 7 (very much).",
    ),
    "vividness_trial": InstrumentInfo(
        instrument_id="vividness_trial",
        name="Trial-Level Vividness Rating",
        version="1.0",
        citation="Study-specific trial-level measure.",
        license_status="study_specific_no_license_required",
        scoring_direction="higher_is_more_vivid",
        items_included=True,
        acquisition_instructions="Per-trial item: 'How vivid was your mental image?' rated 1 (no image) to 7 (perfectly vivid).",
    ),
    "confidence_trial": InstrumentInfo(
        instrument_id="confidence_trial",
        name="Trial-Level Confidence Rating",
        version="1.0",
        citation="Study-specific trial-level measure.",
        license_status="study_specific_no_license_required",
        scoring_direction="higher_is_more_confident",
        items_included=True,
        acquisition_instructions="Per-trial item: 'How confident are you in your vividness rating?' rated 1 (not at all) to 7 (very confident).",
    ),
    "effort_trial": InstrumentInfo(
        instrument_id="effort_trial",
        name="Trial-Level Effort Rating",
        version="1.0",
        citation="Study-specific trial-level measure.",
        license_status="study_specific_no_license_required",
        scoring_direction="higher_is_more_effort",
        items_included=True,
        acquisition_instructions="Per-trial item: 'How much effort did you put into imagining?' rated 1 (no effort) to 7 (maximum effort).",
    ),
    "fatigue_post": InstrumentInfo(
        instrument_id="fatigue_post",
        name="Post-Session Fatigue Rating",
        version="1.0",
        citation="Study-specific post-session measure.",
        license_status="study_specific_no_license_required",
        scoring_direction="higher_is_more_fatigued",
        items_included=True,
        acquisition_instructions="Post-session item: 'How mentally fatigued do you feel?' rated 1 (not at all) to 7 (extremely).",
    ),
    "discomfort_post": InstrumentInfo(
        instrument_id="discomfort_post",
        name="Post-Session Discomfort Rating",
        version="1.0",
        citation="Study-specific post-session measure.",
        license_status="study_specific_no_license_required",
        scoring_direction="higher_is_more_discomfort",
        items_included=True,
        acquisition_instructions="Post-session item: 'Did you experience any discomfort during the session?' rated 1 (none) to 7 (severe).",
    ),
}


def get_instrument(instrument_id: str) -> InstrumentInfo | None:
    return _INSTRUMENTS.get(instrument_id)


def list_instruments() -> list[InstrumentInfo]:
    return list(_INSTRUMENTS.values())
