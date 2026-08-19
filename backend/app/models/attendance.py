"""Attendance record for one enrolment; attendance_rate is derived at write time."""

from datetime import datetime

from sqlmodel import Field

from app.models.base import TimestampedModel


class Attendance(TimestampedModel, table=True):
    __tablename__ = "attendance"

    enrolment_id: int = Field(foreign_key="enrolments.id", index=True, unique=True)
    # Nullable: raw attendance capture is genuinely gap-prone (a register not
    # returned, a sync failure) -- these fields are exactly where the
    # synthetic generator's 4-8% missingness injection lands, so the schema
    # has to tolerate it like the real system would.
    sessions_held: int | None = Field(default=None)
    sessions_attended: int | None = Field(default=None)
    attendance_rate: float | None = Field(default=None)
    last_updated: datetime
