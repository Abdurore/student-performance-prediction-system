"""Unit tests for app.services.student_service's row-level scoping and
query logic -- the part of Section H's role model that lives below the
coarse role checks in app.core.deps."""

import pytest
from sqlmodel import Session, select

from app.models import Course, Enrolment, Student
from app.services.student_service import (
    StudentAccessError,
    assert_can_view_student,
    get_student_profile,
    list_students,
    scope_student_ids,
)


def test_scope_student_ids_admin_sees_everything(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        assert scope_student_ids(session, demo_users["admin"]) is None


def test_scope_student_ids_student_sees_only_self(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        scope = scope_student_ids(session, demo_users["student"])
    assert scope == {demo_users["other_student_id"]}


def test_scope_student_ids_adviser_sees_only_assigned_advisees(small_db_engine, demo_users) -> None:
    """Temporarily assigns the shared `other_student_id` to this adviser and
    reverts it afterwards -- demo_users is module-scoped and reused by other
    tests, so this must not leak state to them."""
    with Session(small_db_engine) as session:
        student = session.get(Student, demo_users["other_student_id"])
        original_adviser_id = student.adviser_id
        student.adviser_id = demo_users["adviser"].id
        session.add(student)
        session.commit()
        try:
            scope = scope_student_ids(session, demo_users["adviser"])
            assert demo_users["other_student_id"] in scope
        finally:
            student.adviser_id = original_adviser_id
            session.add(student)
            session.commit()


def test_scope_student_ids_lecturer_sees_only_students_in_taught_courses(small_db_engine, demo_users) -> None:
    """Temporarily assigns one course to this lecturer and reverts it
    afterwards, for the same reason as the adviser test above."""
    with Session(small_db_engine) as session:
        course = session.exec(select(Course)).first()
        original_lecturer_id = course.lecturer_id
        course.lecturer_id = demo_users["lecturer"].id
        session.add(course)
        session.commit()
        try:
            taught_enrolment_student_ids = set(
                session.exec(select(Enrolment.student_id).where(Enrolment.course_id == course.id)).all()
            )
            scope = scope_student_ids(session, demo_users["lecturer"])
            assert scope == taught_enrolment_student_ids
        finally:
            course.lecturer_id = original_lecturer_id
            session.add(course)
            session.commit()


def test_assert_can_view_student_raises_outside_scope(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        with pytest.raises(StudentAccessError):
            assert_can_view_student(session, demo_users["student"], student_id=1)


def test_assert_can_view_student_allows_own_record(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        assert_can_view_student(session, demo_users["student"], demo_users["other_student_id"])  # no raise


def test_list_students_filters_by_level_and_search(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        result = list_students(session, demo_users["admin"], level=100, page_size=500)
        assert all(item.level == 100 for item in result.items)
        assert result.total == len(result.items) or result.total > len(result.items)

        by_matric = list_students(session, demo_users["admin"], search="ROLE/24/00099")
        assert any(item.matric_no == "ROLE/24/00099" for item in by_matric.items)


def test_list_students_paginates(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        page_1 = list_students(session, demo_users["admin"], page=1, page_size=5)
        page_2 = list_students(session, demo_users["admin"], page=2, page_size=5)
    assert len(page_1.items) == 5
    assert {i.id for i in page_1.items}.isdisjoint({i.id for i in page_2.items})


def test_list_students_scopes_to_student_role(small_db_engine, demo_users) -> None:
    with Session(small_db_engine) as session:
        result = list_students(session, demo_users["student"], page_size=500)
    assert [item.id for item in result.items] == [demo_users["other_student_id"]]


def test_get_student_profile_returns_none_for_unknown_id(small_db_engine) -> None:
    with Session(small_db_engine) as session:
        assert get_student_profile(session, student_id=999_999) is None


def test_get_student_profile_includes_history_and_enrolments(small_db_engine) -> None:
    with Session(small_db_engine) as session:
        any_student_id = session.exec(select(Student.id)).first()
        profile = get_student_profile(session, any_student_id)
    assert profile is not None
    assert profile.id == any_student_id
    assert isinstance(profile.academic_history, list)
    assert isinstance(profile.enrolments, list)
