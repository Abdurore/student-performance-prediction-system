"""Course, enrolment, and attendance endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.deps import get_current_user, get_session, require_admin, require_admin_or_lecturer
from app.models import Attendance, Course, Enrolment, User
from app.models.enums import UserRole
from app.schemas.course import (
    AttendanceRead,
    AttendanceUpdate,
    CourseCreate,
    CourseRead,
    EnrolmentCreate,
    EnrolmentRead,
    ScoreUpdate,
)
from app.services.course_service import EnrolmentAccessError, assert_can_manage_enrolment, update_attendance, update_scores

router = APIRouter(tags=["courses"])


@router.get("/courses", response_model=list[CourseRead])
def get_courses(
    department: str | None = None,
    level: int | None = None,
    semester: str | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[Course]:
    query = select(Course)
    if department is not None:
        query = query.where(Course.department == department)
    if level is not None:
        query = query.where(Course.level == level)
    if semester is not None:
        query = query.where(Course.semester == semester)
    return session.exec(query).all()


@router.post("/courses", response_model=CourseRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_course(payload: CourseCreate, session: Session = Depends(get_session)) -> Course:
    existing = session.exec(select(Course).where(Course.course_code == payload.course_code)).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A course with this course_code already exists.")
    course = Course(**payload.model_dump())
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


def _scope_enrolment_query(query, current_user: User):
    if current_user.role == UserRole.ADMIN:
        return query
    if current_user.role == UserRole.LECTURER:
        taught_course_ids = select(Course.id).where(Course.lecturer_id == current_user.id)
        return query.where(Enrolment.course_id.in_(taught_course_ids))
    if current_user.role == UserRole.ADVISER:
        from app.models import Student

        assigned_ids = select(Student.id).where(Student.adviser_id == current_user.id)
        return query.where(Enrolment.student_id.in_(assigned_ids))
    if current_user.role == UserRole.STUDENT:
        return query.where(Enrolment.student_id == current_user.student_id)
    return query.where(False)


@router.get("/enrolments", response_model=list[EnrolmentRead])
def get_enrolments(
    student_id: int | None = None,
    course_id: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[Enrolment]:
    query = _scope_enrolment_query(select(Enrolment), current_user)
    if student_id is not None:
        query = query.where(Enrolment.student_id == student_id)
    if course_id is not None:
        query = query.where(Enrolment.course_id == course_id)
    return session.exec(query).all()


@router.post("/enrolments", response_model=EnrolmentRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_enrolment(payload: EnrolmentCreate, session: Session = Depends(get_session)) -> Enrolment:
    enrolment = Enrolment(**payload.model_dump())
    session.add(enrolment)
    session.commit()
    session.refresh(enrolment)
    return enrolment


@router.put("/enrolments/{enrolment_id}/scores", response_model=EnrolmentRead, dependencies=[Depends(require_admin_or_lecturer)])
def put_scores(
    enrolment_id: int,
    payload: ScoreUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Enrolment:
    enrolment = session.get(Enrolment, enrolment_id)
    if enrolment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrolment not found.")
    try:
        assert_can_manage_enrolment(session, current_user, enrolment)
    except EnrolmentAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return update_scores(session, enrolment, payload.ca_score, payload.exam_score)


@router.put("/attendance/{enrolment_id}", response_model=AttendanceRead, dependencies=[Depends(require_admin_or_lecturer)])
def put_attendance(
    enrolment_id: int,
    payload: AttendanceUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Attendance:
    enrolment = session.get(Enrolment, enrolment_id)
    if enrolment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrolment not found.")
    try:
        assert_can_manage_enrolment(session, current_user, enrolment)
    except EnrolmentAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return update_attendance(session, enrolment_id, payload.sessions_held, payload.sessions_attended)
