"""Application user accounts (login identities), distinct from student records."""

from sqlalchemy import Column, ForeignKey, Integer
from sqlmodel import Field

from app.models.base import TimestampedModel
from app.models.enums import UserRole, db_enum


class User(TimestampedModel, table=True):
    __tablename__ = "users"

    email: str = Field(unique=True, index=True)
    password_hash: str
    full_name: str
    role: UserRole = Field(sa_column=Column(db_enum(UserRole), index=True, nullable=False))
    # use_alter breaks the users<->students FK cycle (students.adviser_id -> users.id)
    # so both tables can be created without a chicken-and-egg ordering problem.
    student_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("students.id", use_alter=True, name="fk_users_student_id"),
            index=True,
            nullable=True,
        ),
    )
    is_active: bool = Field(default=True)
