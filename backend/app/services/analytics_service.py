"""Dashboard analytics: computed live from the database and current models,
never precomputed/mocked snapshots."""

from __future__ import annotations

import pandas as pd
from sqlmodel import Session, select

from app.models import AcademicHistory, Course, Enrolment, Intervention, Student
from app.models.enums import EnrolmentStatus, InterventionStatus
from app.schemas.analytics import (
    CourseDifficultyItem,
    CourseDifficultyResponse,
    CorrelationsResponse,
    OverviewResponse,
    SessionGpaPoint,
    TrendsResponse,
)
from app.services.prediction_service import bulk_risk_scores
from ml.features import build_semester_features, column_types
from ml.preprocessing import load_raw_tables


def get_overview(session: Session) -> OverviewResponse:
    total_students = len(session.exec(select(Student.id)).all())
    active_students = len(session.exec(select(Student.id).where(Student.is_active == True)).all())  # noqa: E712

    tier_counts = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
    scores = bulk_risk_scores()
    if not scores.empty:
        for tier, count in scores["risk_tier"].value_counts().items():
            tier_counts[tier] = int(count)

    history_rows = session.exec(select(AcademicHistory)).all()
    latest_cgpa_by_student: dict[int, float] = {}
    for row in sorted(history_rows, key=lambda h: (h.session, h.semester)):
        latest_cgpa_by_student[row.student_id] = row.cgpa
    average_cgpa = sum(latest_cgpa_by_student.values()) / len(latest_cgpa_by_student) if latest_cgpa_by_student else 0.0

    open_interventions = len(
        session.exec(
            select(Intervention).where(
                Intervention.status.in_([InterventionStatus.PLANNED, InterventionStatus.IN_PROGRESS])
            )
        ).all()
    )

    return OverviewResponse(
        total_students=total_students,
        active_students=active_students,
        at_risk_low=tier_counts["low"],
        at_risk_moderate=tier_counts["moderate"],
        at_risk_high=tier_counts["high"],
        at_risk_critical=tier_counts["critical"],
        average_cgpa=round(average_cgpa, 3),
        total_interventions_open=open_interventions,
    )


def get_trends(session: Session) -> TrendsResponse:
    history_rows = session.exec(select(AcademicHistory)).all()
    if not history_rows:
        return TrendsResponse(points=[])
    df = pd.DataFrame([h.model_dump() for h in history_rows])
    grouped = df.groupby("session").agg(
        average_gpa=("gpa", "mean"), average_cgpa=("cgpa", "mean"), n_students=("student_id", "nunique")
    ).reset_index()
    grouped = grouped.sort_values("session")
    points = [
        SessionGpaPoint(
            session=row["session"], average_gpa=round(row["average_gpa"], 3),
            average_cgpa=round(row["average_cgpa"], 3), n_students=int(row["n_students"]),
        )
        for _, row in grouped.iterrows()
    ]
    return TrendsResponse(points=points)


def get_correlations() -> CorrelationsResponse:
    """Pearson correlation matrix over the numeric T1/T2 training features."""
    raw = load_raw_tables()
    X, _y, _meta = build_semester_features(raw)
    numeric_cols, _categorical_cols = column_types(X)
    corr = X[numeric_cols].corr(numeric_only=True).round(3)
    corr = corr.fillna(0.0)
    return CorrelationsResponse(features=list(corr.columns), matrix=corr.values.tolist())


def get_course_difficulty(session: Session) -> CourseDifficultyResponse:
    enrolments = session.exec(select(Enrolment).where(Enrolment.status == EnrolmentStatus.COMPLETED)).all()
    if not enrolments:
        return CourseDifficultyResponse(items=[])
    df = pd.DataFrame([e.model_dump() for e in enrolments]).dropna(subset=["total_score"])
    grouped = df.groupby("course_id").agg(
        n_completed=("id", "count"), average_score=("total_score", "mean"),
        failure_rate=("grade", lambda s: (s == "F").mean()),
    ).reset_index()

    courses_by_id = {c.id: c for c in session.exec(select(Course)).all()}
    items = []
    for _, row in grouped.sort_values("failure_rate", ascending=False).iterrows():
        course = courses_by_id.get(int(row["course_id"]))
        if course is None:
            continue
        items.append(
            CourseDifficultyItem(
                course_id=course.id, course_code=course.course_code, title=course.title,
                department=course.department, n_completed=int(row["n_completed"]),
                average_score=round(float(row["average_score"]), 2), failure_rate=round(float(row["failure_rate"]), 3),
            )
        )
    return CourseDifficultyResponse(items=items)
