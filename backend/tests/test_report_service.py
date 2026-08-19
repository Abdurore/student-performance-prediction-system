"""Unit tests for app.services.report_service: real reportlab PDF bytes,
not stubs (Section C's "never mock a value shown to the user" applies to
generated files too)."""

from sqlmodel import Session, select

from app.models import Student
from app.services.report_service import generate_at_risk_report, generate_student_report


def test_generate_student_report_returns_a_real_pdf(small_db_engine) -> None:
    with Session(small_db_engine) as session:
        student_id = session.exec(select(Student.id)).first()
        pdf_bytes = generate_student_report(session, student_id)
    assert pdf_bytes is not None
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


def test_generate_student_report_returns_none_for_unknown_student(small_db_engine) -> None:
    with Session(small_db_engine) as session:
        assert generate_student_report(session, student_id=999_999) is None


def test_generate_at_risk_report_returns_a_real_pdf(api_client, small_db_engine) -> None:
    with Session(small_db_engine) as session:
        pdf_bytes = generate_at_risk_report(session)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500
