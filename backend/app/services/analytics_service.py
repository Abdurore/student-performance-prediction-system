"""Dashboard analytics: computed live from the database and current models,
never precomputed/mocked snapshots."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sqlmodel import Session, select

from app.models import AcademicHistory, Attendance, Course, Enrolment, Intervention, Student
from app.models.enums import EnrolmentStatus, InterventionStatus
from app.schemas.analytics import (
    AttendancePerformancePoint,
    AttendancePerformanceResponse,
    CourseDifficultyItem,
    CourseDifficultyResponse,
    CorrelationsResponse,
    GpaDistributionResponse,
    GpaHistogramBucket,
    LevelComparisonItem,
    LevelComparisonResponse,
    OverviewResponse,
    SessionGpaPoint,
    TrendsResponse,
)
from app.services.prediction_service import bulk_risk_scores
from ml.features import build_semester_features, column_types
from ml.preprocessing import load_raw_tables

GPA_BUCKET_WIDTH = 0.5
ATTENDANCE_PERFORMANCE_SAMPLE_CAP = 1500


def _latest_academic_history_by_student(session: Session) -> dict[int, AcademicHistory]:
    """Each student's most recent (session, semester) academic_history row."""
    history_rows = session.exec(select(AcademicHistory)).all()
    latest: dict[int, AcademicHistory] = {}
    for row in sorted(history_rows, key=lambda h: (h.session, h.semester)):
        latest[row.student_id] = row
    return latest


def get_overview(session: Session) -> OverviewResponse:
    total_students = len(session.exec(select(Student.id)).all())
    active_students = len(session.exec(select(Student.id).where(Student.is_active == True)).all())  # noqa: E712

    tier_counts = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
    scores = bulk_risk_scores()
    if not scores.empty:
        for tier, count in scores["risk_tier"].value_counts().items():
            tier_counts[tier] = int(count)

    latest_history = _latest_academic_history_by_student(session)
    average_cgpa = (
        sum(h.cgpa for h in latest_history.values()) / len(latest_history) if latest_history else 0.0
    )

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


def get_gpa_distribution(session: Session) -> GpaDistributionResponse:
    """Histogram of each student's most recent semester GPA, in fixed
    0.5-wide buckets across the full [0, GPA_SCALE] range."""
    from app.core.academic_config import GPA_SCALE

    latest_history = _latest_academic_history_by_student(session)
    n_buckets = int(round(GPA_SCALE / GPA_BUCKET_WIDTH))
    counts = [0] * n_buckets
    for history in latest_history.values():
        index = min(int(history.gpa // GPA_BUCKET_WIDTH), n_buckets - 1)
        counts[max(index, 0)] += 1

    buckets = [
        GpaHistogramBucket(
            range_low=round(i * GPA_BUCKET_WIDTH, 2),
            range_high=round((i + 1) * GPA_BUCKET_WIDTH, 2),
            count=counts[i],
        )
        for i in range(n_buckets)
    ]
    return GpaDistributionResponse(buckets=buckets, n_students=len(latest_history))


def get_attendance_performance(session: Session) -> AttendancePerformanceResponse:
    """Attendance rate vs. final score across every completed enrolment,
    with a least-squares regression line fitted on the *full* dataset.

    The scatter itself is capped to a random sample for the response --
    tens of thousands of raw points would bloat the payload and stall
    client-side rendering without adding information a sample doesn't
    already convey -- but the fitted line uses every qualifying row, and
    the response reports both n_total and n_sampled so that's not hidden.
    """
    rows = session.exec(
        select(Enrolment.total_score, Attendance.attendance_rate)
        .join(Attendance, Attendance.enrolment_id == Enrolment.id)
        .where(
            Enrolment.status == EnrolmentStatus.COMPLETED,
            Enrolment.total_score.is_not(None),
            Attendance.attendance_rate.is_not(None),
        )
    ).all()

    if not rows:
        return AttendancePerformanceResponse(points=[], slope=0.0, intercept=0.0, n_total=0, n_sampled=0)

    df = pd.DataFrame(rows, columns=["total_score", "attendance_rate"])
    slope, intercept = np.polyfit(df["attendance_rate"], df["total_score"], deg=1)

    sample = df if len(df) <= ATTENDANCE_PERFORMANCE_SAMPLE_CAP else df.sample(
        n=ATTENDANCE_PERFORMANCE_SAMPLE_CAP, random_state=42
    )
    points = [
        AttendancePerformancePoint(attendance_rate=round(float(r.attendance_rate), 4), total_score=round(float(r.total_score), 2))
        for r in sample.itertuples()
    ]
    return AttendancePerformanceResponse(
        points=points, slope=round(float(slope), 4), intercept=round(float(intercept), 4),
        n_total=len(df), n_sampled=len(sample),
    )


def get_level_comparison(session: Session) -> LevelComparisonResponse:
    """GPA/CGPA averages and risk-tier distribution per student level."""
    latest_history = _latest_academic_history_by_student(session)
    students = session.exec(select(Student)).all()
    level_by_student = {s.id: s.level for s in students}

    risk_by_student: dict[int, str] = {}
    scores = bulk_risk_scores()
    if not scores.empty:
        risk_by_student = dict(zip(scores["student_id"], scores["risk_tier"]))

    per_level: dict[int, dict] = {}
    for student_id, level in level_by_student.items():
        bucket = per_level.setdefault(
            level, {"gpas": [], "cgpas": [], "tiers": {"low": 0, "moderate": 0, "high": 0, "critical": 0}}
        )
        history = latest_history.get(student_id)
        if history is not None:
            bucket["gpas"].append(history.gpa)
            bucket["cgpas"].append(history.cgpa)
        tier = risk_by_student.get(student_id)
        if tier is not None:
            bucket["tiers"][tier] += 1

    levels = []
    for level in sorted(per_level):
        bucket = per_level[level]
        levels.append(
            LevelComparisonItem(
                level=level,
                n_students=sum(1 for sid, lvl in level_by_student.items() if lvl == level),
                average_gpa=round(sum(bucket["gpas"]) / len(bucket["gpas"]), 3) if bucket["gpas"] else 0.0,
                average_cgpa=round(sum(bucket["cgpas"]) / len(bucket["cgpas"]), 3) if bucket["cgpas"] else 0.0,
                at_risk_low=bucket["tiers"]["low"], at_risk_moderate=bucket["tiers"]["moderate"],
                at_risk_high=bucket["tiers"]["high"], at_risk_critical=bucket["tiers"]["critical"],
            )
        )
    return LevelComparisonResponse(levels=levels)
