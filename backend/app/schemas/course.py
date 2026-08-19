"""Course and enrolment request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.academic_config import CONTINUOUS_ASSESSMENT_WEIGHT, EXAMINATION_WEIGHT
from app.models.enums import EnrolmentStatus


class CourseCreate(BaseModel):
    course_code: str = Field(min_length=1)
    title: str = Field(min_length=1)
    credit_units: int = Field(ge=1, le=6)
    level: int
    semester: str
    department: str
    lecturer_id: int | None = None
    is_core: bool = True


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_code: str
    title: str
    credit_units: int
    level: int
    semester: str
    department: str
    lecturer_id: int | None
    is_core: bool
    created_at: datetime


class EnrolmentCreate(BaseModel):
    student_id: int
    course_id: int
    session: str
    semester: str


class EnrolmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    course_id: int
    session: str
    semester: str
    ca_score: float | None
    exam_score: float | None
    total_score: float | None
    grade: str | None
    grade_point: int | None
    status: EnrolmentStatus
    is_carryover: bool


class ScoreUpdate(BaseModel):
    ca_score: float | None = Field(default=None, ge=0, le=CONTINUOUS_ASSESSMENT_WEIGHT)
    exam_score: float | None = Field(default=None, ge=0, le=EXAMINATION_WEIGHT)


class AttendanceUpdate(BaseModel):
    sessions_held: int = Field(ge=0)
    sessions_attended: int = Field(ge=0)


class AttendanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    enrolment_id: int
    sessions_held: int | None
    sessions_attended: int | None
    attendance_rate: float | None
