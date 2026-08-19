"""Student records: the academic subject being tracked and predicted for."""

from datetime import date

from sqlalchemy import Column
from sqlmodel import Field

from app.models.base import TimestampedModel
from app.models.enums import Accommodation, EmploymentStatus, Gender, db_enum


class Student(TimestampedModel, table=True):
    __tablename__ = "students"

    matric_no: str = Field(unique=True, index=True)
    first_name: str
    last_name: str
    gender: Gender = Field(sa_column=Column(db_enum(Gender), nullable=False))
    date_of_birth: date
    department: str = Field(index=True)
    programme: str
    level: int = Field(index=True)
    entry_mode: str
    entry_score: float
    state_of_origin: str
    accommodation: Accommodation = Field(sa_column=Column(db_enum(Accommodation), nullable=False))
    has_scholarship: bool = Field(default=False)
    employment_status: EmploymentStatus = Field(
        sa_column=Column(db_enum(EmploymentStatus), nullable=False, default=EmploymentStatus.NONE)
    )
    adviser_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    enrolment_session: str = Field(index=True)
    is_active: bool = Field(default=True, index=True)
