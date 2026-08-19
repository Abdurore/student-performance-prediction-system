"""A student's registration for one course in one session/semester."""

from sqlalchemy import Column
from sqlmodel import Field

from app.models.base import TimestampedModel
from app.models.enums import EnrolmentStatus, db_enum


class Enrolment(TimestampedModel, table=True):
    __tablename__ = "enrolments"

    student_id: int = Field(foreign_key="students.id", index=True)
    course_id: int = Field(foreign_key="courses.id", index=True)
    session: str = Field(index=True)
    semester: str = Field(index=True)
    ca_score: float | None = Field(default=None)
    exam_score: float | None = Field(default=None)
    total_score: float | None = Field(default=None)
    grade: str | None = Field(default=None)
    grade_point: int | None = Field(default=None)
    status: EnrolmentStatus = Field(
        sa_column=Column(db_enum(EnrolmentStatus), index=True, nullable=False, default=EnrolmentStatus.ONGOING)
    )
    is_carryover: bool = Field(default=False)
