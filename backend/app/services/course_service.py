"""Course/enrolment/attendance business logic, including score/grade computation."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.academic_config import grade_for_score
from app.models import Attendance, Course, Enrolment, User
from app.models.enums import EnrolmentStatus, UserRole


class EnrolmentAccessError(PermissionError):
    """Raised when the current user may not write scores/attendance for an enrolment's course."""


def assert_can_manage_enrolment(session: Session, current_user: User, enrolment: Enrolment) -> None:
    if current_user.role == UserRole.ADMIN:
        return
    if current_user.role == UserRole.LECTURER:
        course = session.get(Course, enrolment.course_id)
        if course is not None and course.lecturer_id == current_user.id:
            return
    raise EnrolmentAccessError("Only the course's lecturer or an admin may update scores/attendance.")


def update_scores(session: Session, enrolment: Enrolment, ca_score: float | None, exam_score: float | None) -> Enrolment:
    """Apply CA/exam score updates and recompute total/grade once both are present."""
    if ca_score is not None:
        enrolment.ca_score = ca_score
    if exam_score is not None:
        enrolment.exam_score = exam_score

    if enrolment.ca_score is not None and enrolment.exam_score is not None:
        total = enrolment.ca_score + enrolment.exam_score
        grade, grade_point = grade_for_score(total)
        enrolment.total_score = round(total, 2)
        enrolment.grade = grade
        enrolment.grade_point = grade_point
        enrolment.status = EnrolmentStatus.COMPLETED
        enrolment.is_carryover = grade == "F"

    session.add(enrolment)
    session.commit()
    session.refresh(enrolment)
    return enrolment


def update_attendance(session: Session, enrolment_id: int, sessions_held: int, sessions_attended: int) -> Attendance:
    attendance = session.exec(select(Attendance).where(Attendance.enrolment_id == enrolment_id)).first()
    rate = (sessions_attended / sessions_held) if sessions_held > 0 else None
    if attendance is None:
        attendance = Attendance(
            enrolment_id=enrolment_id, sessions_held=sessions_held, sessions_attended=sessions_attended,
            attendance_rate=rate, last_updated=datetime.now(timezone.utc),
        )
    else:
        attendance.sessions_held = sessions_held
        attendance.sessions_attended = sessions_attended
        attendance.attendance_rate = rate
        attendance.last_updated = datetime.now(timezone.utc)
    session.add(attendance)
    session.commit()
    session.refresh(attendance)
    return attendance
