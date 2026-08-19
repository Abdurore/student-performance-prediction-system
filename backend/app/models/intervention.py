"""Advising action taken in response to a student's risk profile."""

from datetime import datetime

from sqlalchemy import Column
from sqlmodel import Field

from app.models.base import TimestampedModel
from app.models.enums import InterventionActionType, InterventionStatus, db_enum


class Intervention(TimestampedModel, table=True):
    __tablename__ = "interventions"

    student_id: int = Field(foreign_key="students.id", index=True)
    prediction_id: int | None = Field(default=None, foreign_key="predictions.id", index=True)
    created_by: int = Field(foreign_key="users.id", index=True)
    action_type: InterventionActionType = Field(
        sa_column=Column(db_enum(InterventionActionType), index=True, nullable=False)
    )
    notes: str | None = Field(default=None)
    status: InterventionStatus = Field(
        sa_column=Column(db_enum(InterventionStatus), index=True, nullable=False, default=InterventionStatus.PLANNED)
    )
    outcome_note: str | None = Field(default=None)
    resolved_at: datetime | None = Field(default=None)
