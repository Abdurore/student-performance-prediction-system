"""Verify the seeded database against the Phase 1 gate.

Unlike ml.data_generator's calibration_report (which checks the in-memory
dataset right after generation), this script reads back whatever is
currently stored in the database -- so it also catches bugs introduced
between generation and persistence (type coercion, NULL handling, etc.)
and can be re-run any time against an already-seeded database.

    python -m scripts.verify_seed
"""

from __future__ import annotations

import json

import pandas as pd
from sqlmodel import Session

from app.db.session import engine
from ml.data_generator import classify_cgpa  # reuse the same classification bands


def _load(query: str) -> pd.DataFrame:
    with Session(engine) as session:
        return pd.read_sql(query, session.connection())


def verify() -> dict:
    students = _load("SELECT id, department, level, is_active FROM students")
    enrolments = _load(
        "SELECT id, student_id, session, semester, ca_score, exam_score, total_score, status "
        "FROM enrolments"
    )
    attendance = _load("SELECT enrolment_id, attendance_rate FROM attendance")
    engagement = _load(
        "SELECT student_id, assignments_submitted, study_hours_per_week FROM engagement"
    )
    history = _load("SELECT student_id, session, semester, gpa, cgpa FROM academic_history")

    joined = enrolments.merge(attendance, left_on="id", right_on="enrolment_id", how="inner").dropna(
        subset=["attendance_rate", "ca_score"]
    )
    completed = joined.dropna(subset=["total_score"])

    history_sorted = history.sort_values(["student_id", "session", "semester"]).reset_index(drop=True)
    history_sorted["prior_cgpa"] = history_sorted.groupby("student_id")["cgpa"].shift(1)
    prior_next = history_sorted.dropna(subset=["prior_cgpa"])

    latest_cgpa = (
        history.sort_values(["student_id", "session", "semester"]).groupby("student_id").tail(1)["cgpa"]
    )
    classification_dist = latest_cgpa.apply(classify_cgpa).value_counts(normalize=True).round(3).to_dict()

    missingness = {
        "attendance_rate_pct_null": round(100 * attendance["attendance_rate"].isna().mean(), 2),
        "study_hours_pct_null": round(100 * engagement["study_hours_per_week"].isna().mean(), 2),
    }

    report = {
        "n_students": int(students.shape[0]),
        "n_active_students": int(students["is_active"].sum()),
        "n_enrolments": int(enrolments.shape[0]),
        "n_ongoing_enrolments": int((enrolments["status"] == "ongoing").sum()),
        "correlation_matrix": {
            "attendance_rate_vs_ca_score": round(float(joined["attendance_rate"].corr(joined["ca_score"])), 3),
            "attendance_rate_vs_total_score": round(
                float(completed["attendance_rate"].corr(completed["total_score"])), 3
            ),
            "prior_cgpa_vs_next_gpa": round(float(prior_next["prior_cgpa"].corr(prior_next["gpa"])), 3),
        },
        "target_correlations": {
            "attendance_rate_vs_ca_score": 0.55,
            "attendance_rate_vs_total_score": 0.45,
            "prior_cgpa_vs_next_gpa": 0.65,
        },
        "classification_distribution": classification_dist,
        "missingness": missingness,
    }
    return report


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
