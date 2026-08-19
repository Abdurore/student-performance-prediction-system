"""Analytics dashboard response schemas."""

from pydantic import BaseModel


class OverviewResponse(BaseModel):
    total_students: int
    active_students: int
    at_risk_low: int
    at_risk_moderate: int
    at_risk_high: int
    at_risk_critical: int
    average_cgpa: float
    total_interventions_open: int


class SessionGpaPoint(BaseModel):
    session: str
    average_gpa: float
    average_cgpa: float
    n_students: int


class TrendsResponse(BaseModel):
    points: list[SessionGpaPoint]


class CorrelationsResponse(BaseModel):
    features: list[str]
    matrix: list[list[float]]


class CourseDifficultyItem(BaseModel):
    course_id: int
    course_code: str
    title: str
    department: str
    n_completed: int
    average_score: float
    failure_rate: float


class CourseDifficultyResponse(BaseModel):
    items: list[CourseDifficultyItem]
