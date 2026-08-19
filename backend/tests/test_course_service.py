"""Unit tests for app.services.course_service: score/grade computation and
the write-access boundary between admin/lecturer roles."""

import pytest
from sqlmodel import Session, select

from app.models import Attendance, Course, Enrolment
from app.models.enums import EnrolmentStatus
from app.services.course_service import (
    EnrolmentAccessError,
    assert_can_manage_enrolment,
    update_attendance,
    update_scores,
)


def _any_enrolment(session: Session) -> Enrolment:
    return session.exec(select(Enrolment)).first()


def test_assert_can_manage_enrolment_allows_admin(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        enrolment = _any_enrolment(session)
        assert_can_manage_enrolment(session, demo_users["admin"], enrolment)  # no raise


def test_assert_can_manage_enrolment_allows_the_teaching_lecturer(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        enrolment = _any_enrolment(session)
        course = session.get(Course, enrolment.course_id)
        original_lecturer_id = course.lecturer_id
        course.lecturer_id = demo_users["lecturer"].id
        session.add(course)
        session.commit()
        try:
            assert_can_manage_enrolment(session, demo_users["lecturer"], enrolment)  # no raise
        finally:
            course.lecturer_id = original_lecturer_id
            session.add(course)
            session.commit()


def test_assert_can_manage_enrolment_rejects_a_different_lecturer(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        enrolment = _any_enrolment(session)
        course = session.get(Course, enrolment.course_id)
        course.lecturer_id = 999_999  # guaranteed not to be demo_users["lecturer"].id
        session.add(course)
        session.commit()
        with pytest.raises(EnrolmentAccessError):
            assert_can_manage_enrolment(session, demo_users["lecturer"], enrolment)


def test_assert_can_manage_enrolment_rejects_adviser(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        enrolment = _any_enrolment(session)
        with pytest.raises(EnrolmentAccessError):
            assert_can_manage_enrolment(session, demo_users["adviser"], enrolment)


def test_update_scores_computes_total_grade_and_carryover_once_both_scores_present(small_db_engine) -> None:
    with Session(small_db_engine) as session:
        enrolment = Enrolment(
            student_id=1, course_id=1, session="2099/2100", semester="1",
            status=EnrolmentStatus.ONGOING,
        )
        session.add(enrolment)
        session.commit()
        session.refresh(enrolment)

        # CA only: no grade yet.
        updated = update_scores(session, enrolment, ca_score=10.0, exam_score=None)
        assert updated.grade is None
        assert updated.status == EnrolmentStatus.ONGOING

        # Exam recorded too: total/grade/status/carryover all computed.
        updated = update_scores(session, enrolment, ca_score=None, exam_score=15.0)
        assert updated.total_score == 25.0
        assert updated.status == EnrolmentStatus.COMPLETED
        assert updated.grade == "F"  # below the 40-point E/F boundary
        assert updated.is_carryover is True


def test_update_scores_passing_total_is_not_a_carryover(small_db_engine) -> None:
    with Session(small_db_engine) as session:
        enrolment = Enrolment(
            student_id=1, course_id=1, session="2099/2100", semester="2",
            status=EnrolmentStatus.ONGOING, ca_score=28.0,
        )
        session.add(enrolment)
        session.commit()
        session.refresh(enrolment)

        updated = update_scores(session, enrolment, ca_score=None, exam_score=60.0)
        assert updated.total_score == 88.0
        assert updated.grade == "A"
        assert updated.is_carryover is False


def test_update_attendance_creates_a_row_when_none_exists(small_db_engine) -> None:
    with Session(small_db_engine) as session:
        enrolment = Enrolment(student_id=1, course_id=1, session="2099/2100", semester="1")
        session.add(enrolment)
        session.commit()
        session.refresh(enrolment)

        attendance = update_attendance(session, enrolment.id, sessions_held=10, sessions_attended=7)
        assert attendance.attendance_rate == pytest.approx(0.7)


def test_update_attendance_updates_an_existing_row(small_db_engine) -> None:
    with Session(small_db_engine) as session:
        enrolment = Enrolment(student_id=1, course_id=1, session="2099/2100", semester="2")
        session.add(enrolment)
        session.commit()
        session.refresh(enrolment)
        update_attendance(session, enrolment.id, sessions_held=10, sessions_attended=5)

        attendance = update_attendance(session, enrolment.id, sessions_held=10, sessions_attended=9)
        assert attendance.attendance_rate == pytest.approx(0.9)
        rows = session.exec(select(Attendance).where(Attendance.enrolment_id == enrolment.id)).all()
        assert len(rows) == 1  # updated in place, not duplicated


def test_update_attendance_handles_zero_sessions_held(small_db_engine) -> None:
    with Session(small_db_engine) as session:
        enrolment = Enrolment(student_id=1, course_id=1, session="2099/2100", semester="1")
        session.add(enrolment)
        session.commit()
        session.refresh(enrolment)

        attendance = update_attendance(session, enrolment.id, sessions_held=0, sessions_attended=0)
        assert attendance.attendance_rate is None
