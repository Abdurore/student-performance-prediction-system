"""Per-student, per-semester engagement signals used as prediction features."""

from sqlmodel import Field

from app.models.base import TimestampedModel


class Engagement(TimestampedModel, table=True):
    __tablename__ = "engagement"

    student_id: int = Field(foreign_key="students.id", index=True)
    session: str = Field(index=True)
    semester: str = Field(index=True)
    # Nullable: these are self-reported/system-logged signals that
    # genuinely go missing (a system not synced, a survey unanswered) --
    # the synthetic generator's 4-8% missingness injection targets exactly
    # these columns, so cleaning is a real exercise rather than a no-op.
    assignments_submitted: int | None = Field(default=None)
    assignments_total: int | None = Field(default=None)
    submission_punctuality_rate: float | None = Field(default=None)
    lms_logins: int | None = Field(default=None)
    library_visits: int | None = Field(default=None)
    study_hours_per_week: float | None = Field(default=None)
    tutorial_attendance: float | None = Field(default=None)
    extracurricular_hours: float | None = Field(default=None)
