"""Per-semester academic standing snapshot, the source of prior-GPA features."""

from sqlalchemy import Column
from sqlmodel import Field

from app.models.base import TimestampedModel
from app.models.enums import AcademicStanding, db_enum


class AcademicHistory(TimestampedModel, table=True):
    __tablename__ = "academic_history"

    student_id: int = Field(foreign_key="students.id", index=True)
    session: str = Field(index=True)
    semester: str = Field(index=True)
    credits_registered: int
    credits_earned: int
    gpa: float
    cgpa: float
    standing: AcademicStanding = Field(sa_column=Column(db_enum(AcademicStanding), index=True, nullable=False))
