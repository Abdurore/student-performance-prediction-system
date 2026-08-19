"""PDF report generation (Section H): real reportlab documents, not stubs."""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlmodel import Session, select

from app.models import Student
from app.services.prediction_service import bulk_risk_scores
from app.services.student_service import get_student_profile

_NAVY = colors.HexColor("#0F2038")
_AMBER = colors.HexColor("#D97706")


def generate_student_report(session: Session, student_id: int) -> bytes | None:
    profile = get_student_profile(session, student_id)
    if profile is None:
        return None

    styles = getSampleStyleSheet()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"Student Report - {profile.matric_no}")
    elements = [
        Paragraph(f"Student Report: {profile.first_name} {profile.last_name}", styles["Title"]),
        Paragraph(f"{profile.matric_no} -- {profile.department}, Level {profile.level}", styles["Normal"]),
        Spacer(1, 16),
        Paragraph("Academic History", styles["Heading2"]),
    ]

    if profile.academic_history:
        history_data = [["Session", "Semester", "GPA", "CGPA", "Standing"]] + [
            [h.session, h.semester, f"{h.gpa:.2f}", f"{h.cgpa:.2f}", h.standing] for h in profile.academic_history
        ]
        history_table = Table(history_data, hAlign="LEFT")
        history_table.setStyle(_table_style())
        elements.append(history_table)
    else:
        elements.append(Paragraph("No completed semesters on record.", styles["Normal"]))

    elements.append(Spacer(1, 16))
    elements.append(Paragraph("Current Enrolments", styles["Heading2"]))
    if profile.enrolments:
        enrolment_data = [["Course", "Session", "CA", "Exam", "Total", "Grade", "Attendance"]] + [
            [
                e.course_code, f"{e.session} S{e.semester}",
                f"{e.ca_score:.1f}" if e.ca_score is not None else "-",
                f"{e.exam_score:.1f}" if e.exam_score is not None else "-",
                f"{e.total_score:.1f}" if e.total_score is not None else "-",
                e.grade or "-",
                f"{e.attendance_rate * 100:.0f}%" if e.attendance_rate is not None else "-",
            ]
            for e in profile.enrolments
        ]
        enrolment_table = Table(enrolment_data, hAlign="LEFT")
        enrolment_table.setStyle(_table_style())
        elements.append(enrolment_table)
    else:
        elements.append(Paragraph("No enrolment records.", styles["Normal"]))

    doc.build(elements)
    return buffer.getvalue()


def generate_at_risk_report(session: Session) -> bytes:
    scores = bulk_risk_scores()
    scores = scores[scores["risk_tier"].isin(["high", "critical"])].sort_values("probability", ascending=False)
    students_by_id = (
        {s.id: s for s in session.exec(select(Student).where(Student.id.in_(scores["student_id"].tolist()))).all()}
        if not scores.empty
        else {}
    )

    styles = getSampleStyleSheet()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="At-Risk Register")
    elements = [
        Paragraph("At-Risk Register", styles["Title"]),
        Paragraph("High and critical risk-tier students, ranked by predicted risk probability.", styles["Normal"]),
        Spacer(1, 16),
    ]

    if scores.empty:
        elements.append(Paragraph("No students currently flagged high or critical risk.", styles["Normal"]))
    else:
        data = [["Matric No.", "Name", "Department", "Level", "Tier", "Probability"]]
        for _, record in scores.iterrows():
            student = students_by_id.get(int(record["student_id"]))
            if student is None:
                continue
            data.append(
                [
                    student.matric_no, f"{student.first_name} {student.last_name}", student.department,
                    str(student.level), record["risk_tier"].capitalize(), f"{record['probability'] * 100:.1f}%",
                ]
            )
        table = Table(data, hAlign="LEFT")
        table.setStyle(_table_style())
        elements.append(table)

    doc.build(elements)
    return buffer.getvalue()


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ]
    )
