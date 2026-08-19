"""Model registry / comparison response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ModelRegistryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: str
    task: str
    algorithm: str
    trained_at: datetime
    training_rows: int
    feature_list: list[str]
    hyperparameters: dict
    metrics: dict
    fairness_report: dict | None
    artifact_path: str
    is_active: bool


class ModelComparisonRow(BaseModel):
    task: str
    algorithm: str
    is_active: bool
    primary_metric_name: str
    primary_metric_value: float | None
    cv_std: float | None
    train_test_gap: float | None
    leakage_flag: bool


class ModelComparisonResponse(BaseModel):
    rows: list[ModelComparisonRow]


class ActivateModelRequest(BaseModel):
    pass


class RetrainRequest(BaseModel):
    tasks: list[str] | None = None


class RetrainResponse(BaseModel):
    status: str
    message: str
