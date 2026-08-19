"""Student query/CRUD business logic, including role-based row scoping.

Row-level scoping (as opposed to the coarse role check in app.core.deps)
lives here: a lecturer sees only students enrolled in courses they teach,
an adviser only their assigned students, a student only themself.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import AcademicHistory, Attendance, Course, Enrolment, Prediction, Student, User
from app.models.enums import PredictionTask, UserRole
from app.schemas.student import (
    AcademicHistoryItem,
    EnrolmentItem,
    PaginatedStudents,
    StudentListItem,
    StudentProfile,
)


class StudentAccessError(PermissionError):
    """Raised when the current user has no access to the requested student."""


def scope_student_ids(session: Session, current_user: User) -> set[int] | None:
    """Return the set of student ids the current user may see, or None for "all"."""
    if current_user.role == UserRole.ADMIN:
        return None
    if current_user.role == UserRole.ADVISER:
        ids = session.exec(select(Student.id).where(Student.adviser_id == current_user.id)).all()
        return set(ids)
    if current_user.role == UserRole.LECTURER:
        taught_course_ids = select(Course.id).where(Course.lecturer_id == current_user.id)
        ids = session.exec(
            select(Enrolment.student_id).where(Enrolment.course_id.in_(taught_course_ids)).distinct()
        ).all()
        return set(ids)
    if current_user.role == UserRole.STUDENT:
        return {current_user.student_id} if current_user.student_id is not None else set()
    return set()


def assert_can_view_student(session: Session, current_user: User, student_id: int) -> None:
    scope = scope_student_ids(session, current_user)
    if scope is not None and student_id not in scope:
        raise StudentAccessError(f"User {current_user.id} may not access student {student_id}.")


def _latest_risk_tiers(session: Session, student_ids: list[int]) -> dict[int, str]:
    if not student_ids:
        return {}
    subq = (
        select(
            Prediction.student_id,
            func.max(Prediction.predicted_at).label("latest_at"),
        )
        .where(Prediction.task == PredictionTask.RISK_CLASSIFICATION, Prediction.student_id.in_(student_ids))
        .group_by(Prediction.student_id)
        .subquery()
    )
    rows = session.exec(
        select(Prediction.student_id, Prediction.risk_tier).join(
            subq,
            (Prediction.student_id == subq.c.student_id) & (Prediction.predicted_at == subq.c.latest_at),
        )
    ).all()
    return {student_id: (risk_tier.value if risk_tier else None) for student_id, risk_tier in rows}


def list_students(
    session: Session,
    current_user: User,
    *,
    level: int | None = None,
    department: str | None = None,
    risk_tier: str | None = None,
    adviser_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedStudents:
    query = select(Student)
    scope = scope_student_ids(session, current_user)
    if scope is not None:
        query = query.where(Student.id.in_(scope)) if scope else query.where(False)
    if level is not None:
        query = query.where(Student.level == level)
    if department is not None:
        query = query.where(Student.department == department)
    if adviser_id is not None:
        query = query.where(Student.adviser_id == adviser_id)
    if search:
        like = f"%{search}%"
        query = query.where(
            (Student.matric_no.ilike(like)) | (Student.first_name.ilike(like)) | (Student.last_name.ilike(like))
        )

    all_matching = session.exec(query).all()
    risk_by_student = _latest_risk_tiers(session, [s.id for s in all_matching])
    if risk_tier is not None:
        all_matching = [s for s in all_matching if risk_by_student.get(s.id) == risk_tier]

    total = len(all_matching)
    start = (page - 1) * page_size
    page_items = all_matching[start : start + page_size]
    items = []
    for student in page_items:
        item = StudentListItem.model_validate(student)
        item.risk_tier = risk_by_student.get(student.id)
        items.append(item)
    return PaginatedStudents(items=items, total=total, page=page, page_size=page_size)


def get_student_profile(session: Session, student_id: int) -> StudentProfile | None:
    student = session.get(Student, student_id)
    if student is None:
        return None

    history_rows = session.exec(
        select(AcademicHistory)
        .where(AcademicHistory.student_id == student_id)
        .order_by(AcademicHistory.session, AcademicHistory.semester)
    ).all()
    history_items = [
        AcademicHistoryItem(
            session=h.session, semester=h.semester, credits_registered=h.credits_registered,
            credits_earned=h.credits_earned, gpa=h.gpa, cgpa=h.cgpa, standing=h.standing.value,
        )
        for h in history_rows
    ]

    enrolment_rows = session.exec(
        select(Enrolment, Course)
        .join(Course, Enrolment.course_id == Course.id)
        .where(Enrolment.student_id == student_id)
        .order_by(Enrolment.session, Enrolment.semester)
    ).all()

    enrolment_ids = [e.id for e, _c in enrolment_rows]
    attendance_by_enrolment = {}
    if enrolment_ids:
        att_rows = session.exec(select(Attendance).where(Attendance.enrolment_id.in_(enrolment_ids))).all()
        attendance_by_enrolment = {a.enrolment_id: a.attendance_rate for a in att_rows}

    enrolment_items = [
        EnrolmentItem(
            course_code=course.course_code, course_title=course.title, session=enrolment.session,
            semester=enrolment.semester, ca_score=enrolment.ca_score, exam_score=enrolment.exam_score,
            total_score=enrolment.total_score, grade=enrolment.grade,
            attendance_rate=attendance_by_enrolment.get(enrolment.id), status=enrolment.status.value,
        )
        for enrolment, course in enrolment_rows
    ]

    return StudentProfile(
        **student.model_dump(),
        academic_history=history_items,
        enrolments=enrolment_items,
    )
