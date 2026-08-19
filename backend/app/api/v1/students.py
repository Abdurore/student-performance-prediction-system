"""Student endpoints: list/detail/CRUD/import."""

import io

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlmodel import Session, select

from app.core.deps import get_current_user, get_session, require_admin
from app.db.csv_import import import_students_csv
from app.models import Student, User
from app.schemas.import_report import ImportReportResponse
from app.schemas.student import PaginatedStudents, StudentCreate, StudentProfile, StudentRead, StudentUpdate
from app.services.student_service import StudentAccessError, assert_can_view_student, get_student_profile, list_students

router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=PaginatedStudents)
def get_students(
    level: int | None = None,
    department: str | None = None,
    risk_tier: str | None = None,
    adviser_id: int | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PaginatedStudents:
    return list_students(
        session, current_user, level=level, department=department, risk_tier=risk_tier,
        adviser_id=adviser_id, search=search, page=page, page_size=page_size,
    )


@router.get("/{student_id}", response_model=StudentProfile)
def get_student(
    student_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> StudentProfile:
    try:
        assert_can_view_student(session, current_user, student_id)
    except StudentAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    profile = get_student_profile(session, student_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return profile


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_student(payload: StudentCreate, session: Session = Depends(get_session)) -> Student:
    existing = session.exec(select(Student).where(Student.matric_no == payload.matric_no)).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A student with this matric_no already exists.")
    student = Student(**payload.model_dump())
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


@router.put("/{student_id}", response_model=StudentRead, dependencies=[Depends(require_admin)])
def update_student(student_id: int, payload: StudentUpdate, session: Session = Depends(get_session)) -> Student:
    student = session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_student(student_id: int, session: Session = Depends(get_session)) -> None:
    student = session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    session.delete(student)
    session.commit()


@router.post("/import", response_model=ImportReportResponse, dependencies=[Depends(require_admin)])
async def import_students(file: UploadFile) -> ImportReportResponse:
    content = await file.read()
    report = import_students_csv(io.StringIO(content.decode("utf-8")))
    return ImportReportResponse(**report.to_dict())
