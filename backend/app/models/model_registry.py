"""Metadata for each trained model artifact, mirroring ml/artifacts/metrics/*.json."""

from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.models.base import TimestampedModel
from app.models.enums import PredictionTask, db_enum


class ModelRegistry(TimestampedModel, table=True):
    __tablename__ = "model_registry"

    version: str = Field(unique=True, index=True)
    task: PredictionTask = Field(sa_column=Column(db_enum(PredictionTask), index=True, nullable=False))
    algorithm: str
    trained_at: datetime
    training_rows: int
    feature_list: list = Field(default_factory=list, sa_column=Column(JSON))
    hyperparameters: dict = Field(default_factory=dict, sa_column=Column(JSON))
    metrics: dict = Field(default_factory=dict, sa_column=Column(JSON))
    fairness_report: dict | None = Field(default=None, sa_column=Column(JSON))
    artifact_path: str
    is_active: bool = Field(default=False, index=True)
