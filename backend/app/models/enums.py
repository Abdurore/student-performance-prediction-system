"""Enumerations shared across SQLModel tables.

Kept separate from academic_config.py because these are storage-layer
vocabularies (roles, statuses) rather than institution-specific academic
rules, which stay centralized per the project's single-source-of-truth
constraint.
"""

from enum import StrEnum
from typing import Any

from sqlalchemy import Enum as SAEnum


def db_enum(enum_cls: type[StrEnum], **kwargs: Any) -> SAEnum:
    """Build a SQLAlchemy Enum type that stores each member's *value*.

    SQLAlchemy's default Enum type persists the member *name* (e.g.
    "ADMIN"), not its value ("admin") -- which would silently break every
    lowercase string the API contract, seed data, and frontend all expect.
    Every enum-typed column must be declared through this helper instead
    of a bare type hint.
    """
    return SAEnum(enum_cls, values_callable=lambda cls: [member.value for member in cls], **kwargs)


class UserRole(StrEnum):
    ADMIN = "admin"
    LECTURER = "lecturer"
    ADVISER = "adviser"
    STUDENT = "student"


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class Accommodation(StrEnum):
    ON_CAMPUS = "on_campus"
    OFF_CAMPUS = "off_campus"


class EmploymentStatus(StrEnum):
    NONE = "none"
    PART_TIME = "part_time"
    FULL_TIME = "full_time"


class Semester(StrEnum):
    FIRST = "1"
    SECOND = "2"


class EnrolmentStatus(StrEnum):
    ONGOING = "ongoing"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


class AcademicStanding(StrEnum):
    GOOD = "good"
    WARNING = "warning"
    PROBATION = "probation"
    WITHDRAWAL = "withdrawal"


class PredictionTask(StrEnum):
    RISK_CLASSIFICATION = "risk_classification"
    GPA_REGRESSION = "gpa_regression"
    COURSE_SCORE = "course_score"


class RiskTier(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class InterventionActionType(StrEnum):
    COUNSELLING = "counselling"
    TUTORIAL = "tutorial"
    GUARDIAN_CONTACT = "guardian_contact"
    WORKLOAD_REVIEW = "workload_review"
    REFERRAL = "referral"
    OTHER = "other"


class InterventionStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
