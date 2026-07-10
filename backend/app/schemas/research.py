from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class StudyMode(str, Enum):
    DEMO = "demo"
    BENCHMARK = "benchmark"
    PILOT = "pilot"
    APPROVED_STUDY = "approved_study"


class FeedbackCondition(str, Enum):
    ADAPTIVE = "adaptive"
    FIXED = "fixed"
    YOKED = "yoked"


class StudyCreate(BaseModel):
    study_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=256)
    protocol_version: str = Field(min_length=1, max_length=64)
    conditions: list[FeedbackCondition] = Field(
        default_factory=lambda: [FeedbackCondition.ADAPTIVE, FeedbackCondition.FIXED, FeedbackCondition.YOKED]
    )
    description: str = ""
    ethics_status: str = "not_submitted"
    ethics_reference: str = ""


class Study(BaseModel):
    study_id: str
    title: str
    protocol_version: str
    conditions: list[FeedbackCondition]
    description: str = ""
    ethics_status: str = "not_submitted"
    ethics_reference: str = ""
    created_at: str = ""
    status: str = "created"


class ParticipantCreate(BaseModel):
    pseudonym: str = Field(min_length=1, max_length=64)
    study_id: str
    eligibility_confirmed: bool = False


class Participant(BaseModel):
    participant_id: str
    pseudonym: str
    study_id: str
    eligibility_confirmed: bool = False
    condition_sequence: list[FeedbackCondition] = Field(default_factory=list)
    sessions_completed: int = 0
    created_at: str = ""
    randomization_seed: int = 0


class ConsentRecord(BaseModel):
    consent_id: str
    participant_id: str
    study_id: str
    consent_version: str
    consented_at: str
    withdrawn: bool = False
    withdrawn_at: Optional[str] = None


class ConsentCreate(BaseModel):
    participant_id: str
    study_id: str
    consent_version: str = Field(min_length=1, max_length=64)


class ConditionAssignment(BaseModel):
    participant_id: str
    study_id: str
    session_index: int = Field(ge=0)
    condition: FeedbackCondition
    assigned_at: str = ""


class ParticipantPublicView(BaseModel):
    participant_id: str
    pseudonym: str
    study_id: str
    eligibility_confirmed: bool = False
    sessions_completed: int = 0
    created_at: str = ""


class ParticipantOperatorView(BaseModel):
    participant_id: str
    pseudonym: str
    study_id: str
    eligibility_confirmed: bool = False
    sessions_completed: int = 0
    created_at: str = ""
    condition_sequence: list[FeedbackCondition] = Field(default_factory=list)
    randomization_seed: int = 0


class InstrumentInfo(BaseModel):
    instrument_id: str
    name: str
    version: str
    citation: str
    license_status: str
    scoring_direction: str
    items_included: bool
    acquisition_instructions: str
