"""Student request/response schemas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Accommodation, EmploymentStatus, Gender


class StudentCreate(BaseModel):
    matric_no: str = Field(min_length=1)
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    gender: Gender
    date_of_birth: date
    department: str = Field(min_length=1)
    programme: str = Field(min_length=1)
    level: int
    entry_mode: str
    entry_score: float = Field(ge=0, le=400)
    state_of_origin: str
    accommodation: Accommodation
    has_scholarship: bool = False
    employment_status: EmploymentStatus = EmploymentStatus.NONE
    adviser_id: int | None = None
    enrolment_session: str


class StudentUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    department: str | None = None
    programme: str | None = None
    level: int | None = None
    accommodation: Accommodation | None = None
    has_scholarship: bool | None = None
    employment_status: EmploymentStatus | None = None
    adviser_id: int | None = None
    is_active: bool | None = None


class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matric_no: str
    first_name: str
    last_name: str
    gender: Gender
    date_of_birth: date
    department: str
    programme: str
    level: int
    entry_mode: str
    entry_score: float
    state_of_origin: str
    accommodation: Accommodation
    has_scholarship: bool
    employment_status: EmploymentStatus
    adviser_id: int | None
    enrolment_session: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StudentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matric_no: str
    first_name: str
    last_name: str
    department: str
    level: int
    adviser_id: int | None
    is_active: bool
    risk_tier: str | None = None


class PaginatedStudents(BaseModel):
    items: list[StudentListItem]
    total: int
    page: int
    page_size: int


class AcademicHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session: str
    semester: str
    credits_registered: int
    credits_earned: int
    gpa: float
    cgpa: float
    standing: str


class EnrolmentItem(BaseModel):
    course_code: str
    course_title: str
    session: str
    semester: str
    ca_score: float | None
    exam_score: float | None
    total_score: float | None
    grade: str | None
    attendance_rate: float | None
    status: str


class StudentProfile(StudentRead):
    academic_history: list[AcademicHistoryItem]
    enrolments: list[EnrolmentItem]
