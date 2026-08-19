"""PDF report endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from app.core.deps import get_current_user, get_session, require_any_staff
from app.services.report_service import generate_at_risk_report, generate_student_report
from app.services.student_service import StudentAccessError, assert_can_view_student

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/student/{student_id}")
def post_student_report(
    student_id: int,
    current_user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    try:
        assert_can_view_student(session, current_user, student_id)
    except StudentAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    pdf_bytes = generate_student_report(session, student_id)
    if pdf_bytes is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="student_{student_id}_report.pdf"'},
    )


@router.post("/at-risk", dependencies=[Depends(require_any_staff)])
def post_at_risk_report(session: Session = Depends(get_session)) -> Response:
    pdf_bytes = generate_at_risk_report(session)
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="at_risk_register.pdf"'},
    )
