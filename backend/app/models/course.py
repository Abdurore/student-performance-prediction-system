"""Course catalogue entries offered per level/semester/department."""

from sqlmodel import Field

from app.models.base import TimestampedModel


class Course(TimestampedModel, table=True):
    __tablename__ = "courses"

    course_code: str = Field(unique=True, index=True)
    title: str
    credit_units: int
    level: int = Field(index=True)
    semester: str = Field(index=True)
    department: str = Field(index=True)
    lecturer_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    is_core: bool = Field(default=True)
