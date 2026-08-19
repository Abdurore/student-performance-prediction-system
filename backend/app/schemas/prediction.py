"""Prediction request/response schemas."""

from pydantic import BaseModel

from app.models.enums import RiskTier


class Contributor(BaseModel):
    feature: str
    rank: int
    shap_value: float
    raw_value: float | str | bool | None
    sentence: str


class RiskPrediction(BaseModel):
    probability: float
    risk_tier: RiskTier
    algorithm: str
    top_factors: list[Contributor]


class GpaPrediction(BaseModel):
    predicted_gpa: float
    predicted_cgpa: float
    interval_low: float
    interval_high: float
    algorithm: str
    top_factors: list[Contributor]


class CourseScorePrediction(BaseModel):
    course_id: int
    course_code: str
    predicted_score: float
    algorithm: str
    top_factors: list[Contributor]


class StudentPredictionResponse(BaseModel):
    student_id: int
    session: str
    semester: str
    risk: RiskPrediction | None
    gpa: GpaPrediction | None
    course_scores: list[CourseScorePrediction]


class BatchPredictionRequest(BaseModel):
    student_ids: list[int] | None = None


class BatchPredictionRow(BaseModel):
    student_id: int
    matric_no: str
    risk_tier: RiskTier | None
    probability: float | None
    predicted_gpa: float | None
    error: str | None = None


class BatchPredictionResponse(BaseModel):
    total_requested: int
    total_succeeded: int
    results: list[BatchPredictionRow]


class AtRiskItem(BaseModel):
    student_id: int
    matric_no: str
    full_name: str
    department: str
    level: int
    risk_tier: RiskTier
    probability: float
    adviser_id: int | None


class AtRiskResponse(BaseModel):
    items: list[AtRiskItem]
    total: int


class ExplanationResponse(BaseModel):
    student_id: int
    task: str
    algorithm: str
    sentences: list[str]
    contributors: list[Contributor]
