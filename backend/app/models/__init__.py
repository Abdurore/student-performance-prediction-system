"""SQLModel table registry.

Importing this package registers every table on SQLModel.metadata, which
Alembic's env.py and the local dev create_all path both rely on.
"""

from app.models.academic_history import AcademicHistory
from app.models.attendance import Attendance
from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.engagement import Engagement
from app.models.enrolment import Enrolment
from app.models.intervention import Intervention
from app.models.model_registry import ModelRegistry
from app.models.prediction import Prediction
from app.models.student import Student
from app.models.user import User

__all__ = [
    "AcademicHistory",
    "Attendance",
    "AuditLog",
    "Course",
    "Engagement",
    "Enrolment",
    "Intervention",
    "ModelRegistry",
    "Prediction",
    "Student",
    "User",
]
