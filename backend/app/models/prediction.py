"""A single model inference for a student, kept for audit and UI display.

Populated by trained ML artifacts starting in Phase 5 — never written by
hand or mocked (see CLAUDE.md / Section C).
"""

from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.models.base import TimestampedModel
from app.models.enums import PredictionTask, RiskTier, db_enum


class Prediction(TimestampedModel, table=True):
    __tablename__ = "predictions"

    student_id: int = Field(foreign_key="students.id", index=True)
    model_version: str = Field(index=True)
    task: PredictionTask = Field(sa_column=Column(db_enum(PredictionTask), index=True, nullable=False))
    predicted_value: float | None = Field(default=None)
    predicted_class: str | None = Field(default=None)
    risk_tier: RiskTier | None = Field(sa_column=Column(db_enum(RiskTier), index=True, nullable=True))
    confidence: float | None = Field(default=None)
    probability: float | None = Field(default=None)
    feature_contributions: dict | None = Field(default=None, sa_column=Column(JSON))
    input_snapshot: dict | None = Field(default=None, sa_column=Column(JSON))
    predicted_at: datetime
