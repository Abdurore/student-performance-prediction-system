"""Intervention request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import InterventionActionType, InterventionStatus


class InterventionCreate(BaseModel):
    student_id: int
    prediction_id: int | None = None
    action_type: InterventionActionType
    notes: str | None = None


class InterventionUpdate(BaseModel):
    status: InterventionStatus | None = None
    notes: str | None = None
    outcome_note: str | None = None


class InterventionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    prediction_id: int | None
    created_by: int
    action_type: InterventionActionType
    notes: str | None
    status: InterventionStatus
    outcome_note: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime
