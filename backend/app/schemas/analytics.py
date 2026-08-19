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


class GpaHistogramBucket(BaseModel):
    range_low: float
    range_high: float
    count: int


class GpaDistributionResponse(BaseModel):
    buckets: list[GpaHistogramBucket]
    n_students: int


class AttendancePerformancePoint(BaseModel):
    attendance_rate: float
    total_score: float


class AttendancePerformanceResponse(BaseModel):
    points: list[AttendancePerformancePoint]
    slope: float
    intercept: float
    n_total: int
    n_sampled: int


class LevelComparisonItem(BaseModel):
    level: int
    n_students: int
    average_gpa: float
    average_cgpa: float
    at_risk_low: int
    at_risk_moderate: int
    at_risk_high: int
    at_risk_critical: int


class LevelComparisonResponse(BaseModel):
    levels: list[LevelComparisonItem]
