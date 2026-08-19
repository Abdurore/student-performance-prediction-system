"""Prediction serving: real inference from trained artifacts, never mocked.

Two paths, deliberately different in cost:
- Bulk scoring (at-risk list, batch): predict_proba/predict only, vectorized
  across every row at once. Full SHAP explanation for hundreds of students
  would take tens of minutes (each single-row explanation costs several
  seconds -- see ml/explain.py); a list view doesn't need per-row
  explanations, just the score.
- Single-student detail (POST /predictions/student/{id}): the full SHAP
  explanation, computed once for that one row.

Every prediction that is *persisted* (POST endpoints) is written with its
complete, unfiltered feature_contributions -- the Section I student-facing
filter is applied only when *serving* a response to a student, never when
storing the record, so the same row backs both the staff and student views.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sqlmodel import Session, select

from app.core.academic_config import GPA_SCALE
from app.models import Course, ModelRegistry, Prediction
from app.models.enums import PredictionTask, RiskTier, UserRole
from ml.config import risk_tier_for_probability
from ml.explain import (
    TOP_N_CONTRIBUTORS,
    compute_shap_values,
    filter_to_modifiable_contributors,
    load_active_pipeline,
    render_sentences,
    render_student_sentences,
    top_contributors,
)
from ml.features import build_course_prediction_features, build_prediction_features
from ml.preprocessing import load_raw_tables

BACKGROUND_SAMPLE_SIZE = 100


def _background(X: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    return X.sample(n=min(BACKGROUND_SAMPLE_SIZE, len(X)), random_state=seed)


def _contributor_dicts(shap_row: np.ndarray, feature_row: pd.Series, task: str) -> list[dict]:
    """Every feature ranked by |SHAP value|, not just the top N.

    Truncation happens later, in contributors_for_role -- not here -- because
    the student-facing view filters to modifiable features *first* and only
    then takes its own top N. Truncating to the staff top-5 up front would
    silently drop modifiable factors ranked 6th-10th overall that might be
    the most actionable ones a student could actually see.
    """
    contributors = top_contributors(shap_row, feature_row, top_n=len(feature_row))
    sentences = render_sentences(contributors, task)
    for contributor, sentence in zip(contributors, sentences):
        contributor["sentence"] = sentence
        contributor["raw_value"] = None if pd.isna(contributor["raw_value"]) else contributor["raw_value"]
    return contributors


def contributors_for_role(contributors: list[dict], task: str, role: UserRole) -> tuple[list[dict], list[str]]:
    """Apply Section I's server-side student-facing filter, or pass staff data through.

    `contributors` is expected to be the *full* ranked list (see
    _contributor_dicts); this function does the top-N truncation itself so
    each view gets its own ranking rather than a subset of the other's.
    """
    if role != UserRole.STUDENT:
        top = contributors[:TOP_N_CONTRIBUTORS]
        return top, [c["sentence"] for c in top]
    filtered = filter_to_modifiable_contributors(contributors, TOP_N_CONTRIBUTORS)
    sentences = render_student_sentences(filtered, task)
    rebuilt = []
    for contributor, sentence in zip(filtered, sentences):
        contributor = {**contributor, "sentence": sentence}
        rebuilt.append(contributor)
    return rebuilt, sentences


def bulk_risk_scores(student_ids: list[int] | None = None) -> pd.DataFrame:
    """Fast, unexplained risk probabilities for every (or the given) active student.

    Returns a DataFrame with student_id, session, semester, probability, risk_tier.
    """
    raw = load_raw_tables()
    X, meta = build_prediction_features(raw)
    if student_ids is not None:
        mask = meta["student_id"].isin(student_ids)
        X, meta = X[mask], meta[mask]
    if X.empty:
        return meta.assign(probability=[], risk_tier=[])

    pipeline, algorithm = load_active_pipeline("risk_classification")
    probabilities = pipeline.predict_proba(X)[:, 1]
    result = meta.copy()
    result["probability"] = probabilities
    result["risk_tier"] = [risk_tier_for_probability(p) for p in probabilities]
    result["algorithm"] = algorithm
    return result.reset_index(drop=True)


def bulk_gpa_scores(student_ids: list[int] | None = None) -> pd.DataFrame:
    """Fast, unexplained GPA point forecasts for every (or the given) active student.

    Mirrors bulk_risk_scores exactly (predict only, no SHAP) -- see the
    module docstring for why bulk scoring and single-student detail are
    deliberately different costs. Shares the same underlying (student,
    session, semester) rows as bulk_risk_scores, since both read from
    build_prediction_features -- a student found by one is found by the
    other. Returns a DataFrame with student_id, session, semester,
    predicted_gpa, algorithm.
    """
    raw = load_raw_tables()
    X, meta = build_prediction_features(raw)
    if student_ids is not None:
        mask = meta["student_id"].isin(student_ids)
        X, meta = X[mask], meta[mask]
    if X.empty:
        return meta.assign(predicted_gpa=[], algorithm=[])

    pipeline, algorithm = load_active_pipeline("gpa_regression")
    predictions = np.clip(pipeline.predict(X), 0, GPA_SCALE)
    result = meta.copy()
    result["predicted_gpa"] = predictions
    result["algorithm"] = algorithm
    return result.reset_index(drop=True)


def _projected_cgpa(predicted_gpa: float, prior_cgpa: float | None, semesters_completed: float) -> float:
    """Credit-agnostic approximation: blend the predicted semester GPA into the
    running CGPA, weighted by how many semesters already contributed to it.
    A precise figure needs per-semester credit loads the feature row doesn't
    carry; this keeps the estimate transparent and defensible for a report
    rather than silently wrong."""
    if prior_cgpa is None or pd.isna(prior_cgpa) or semesters_completed <= 0:
        return predicted_gpa
    return (prior_cgpa * semesters_completed + predicted_gpa) / (semesters_completed + 1)


def predict_student_detail(session: Session, student_id: int) -> dict | None:
    """Full T1 + T2 + T3 prediction with SHAP explanations for one student's
    current semester. Returns None if the student has no ongoing enrolment.
    """
    raw = load_raw_tables()
    X_sem, meta_sem = build_prediction_features(raw)
    sem_mask = meta_sem["student_id"] == student_id
    if not sem_mask.any():
        return None
    sem_idx = meta_sem.index[sem_mask][0]
    session_label, semester_label = meta_sem.loc[sem_idx, "session"], meta_sem.loc[sem_idx, "semester"]
    feature_row = X_sem.loc[[sem_idx]]

    background_sem = _background(X_sem)

    # --- T1: risk ---
    risk_pipeline, risk_algo = load_active_pipeline("risk_classification")
    probability = float(risk_pipeline.predict_proba(feature_row)[0, 1])
    risk_shap = compute_shap_values(risk_pipeline, background_sem, feature_row, "classification")
    risk_contributors = _contributor_dicts(risk_shap[0], feature_row.iloc[0], "risk_classification")

    # --- T2: GPA ---
    gpa_pipeline, gpa_algo = load_active_pipeline("gpa_regression")
    predicted_gpa = float(gpa_pipeline.predict(feature_row)[0])
    predicted_gpa = float(np.clip(predicted_gpa, 0, GPA_SCALE))
    gpa_shap = compute_shap_values(gpa_pipeline, background_sem, feature_row, "regression")
    gpa_contributors = _contributor_dicts(gpa_shap[0], feature_row.iloc[0], "gpa_regression")

    gpa_rmse = _active_model_rmse(session, "gpa_regression")
    prior_cgpa = feature_row.iloc[0].get("prior_cgpa")
    semesters_completed = feature_row.iloc[0].get("semesters_completed", 0) or 0
    projected_cgpa = float(np.clip(_projected_cgpa(predicted_gpa, prior_cgpa, semesters_completed), 0, GPA_SCALE))
    interval_low = float(np.clip(predicted_gpa - gpa_rmse, 0, GPA_SCALE))
    interval_high = float(np.clip(predicted_gpa + gpa_rmse, 0, GPA_SCALE))

    # --- T3: per-ongoing-course scores ---
    X_course, meta_course = build_course_prediction_features(raw)
    course_mask = meta_course["student_id"] == student_id
    course_predictions = []
    if course_mask.any():
        course_pipeline, course_algo = load_active_pipeline("course_score")
        course_rows = X_course[course_mask]
        course_meta_rows = meta_course[course_mask]
        background_course = _background(X_course)
        course_ids = course_meta_rows["course_id"].tolist()
        courses_by_id = {c.id: c for c in session.exec(select(Course).where(Course.id.in_(course_ids))).all()}
        for row_idx in course_rows.index:
            row = course_rows.loc[[row_idx]]
            predicted_score = float(np.clip(course_pipeline.predict(row)[0], 0, 100))
            shap_vals = compute_shap_values(course_pipeline, background_course, row, "regression")
            contributors = _contributor_dicts(shap_vals[0], row.iloc[0], "course_score")
            course_id = int(course_meta_rows.loc[row_idx, "course_id"])
            course = courses_by_id.get(course_id)
            course_predictions.append(
                {
                    "course_id": course_id,
                    "course_code": course.course_code if course else "?",
                    "predicted_score": predicted_score,
                    "algorithm": course_algo,
                    "contributors": contributors,
                }
            )

    return {
        "student_id": student_id,
        "session": session_label,
        "semester": semester_label,
        "risk": {
            "probability": probability,
            "risk_tier": risk_tier_for_probability(probability),
            "algorithm": risk_algo,
            "contributors": risk_contributors,
        },
        "gpa": {
            "predicted_gpa": predicted_gpa,
            "predicted_cgpa": projected_cgpa,
            "interval_low": interval_low,
            "interval_high": interval_high,
            "algorithm": gpa_algo,
            "contributors": gpa_contributors,
        },
        "course_scores": course_predictions,
    }


def _active_model_rmse(session: Session, task: str) -> float:
    row = session.exec(
        select(ModelRegistry).where(ModelRegistry.task == task, ModelRegistry.is_active == True)  # noqa: E712
    ).first()
    if row is None:
        return 0.3
    rmse = row.metrics.get("rmse")
    return float(rmse) if rmse is not None else 0.3


def persist_prediction(
    session: Session,
    *,
    student_id: int,
    task: PredictionTask,
    predicted_value: float | None,
    predicted_class: str | None,
    risk_tier: RiskTier | None,
    confidence: float | None,
    probability: float | None,
    feature_contributions: list[dict],
    input_snapshot: dict,
    model_version: str,
) -> Prediction:
    prediction = Prediction(
        student_id=student_id,
        model_version=model_version,
        task=task,
        predicted_value=predicted_value,
        predicted_class=predicted_class,
        risk_tier=risk_tier,
        confidence=confidence,
        probability=probability,
        feature_contributions={"contributors": feature_contributions},
        input_snapshot=input_snapshot,
        predicted_at=datetime.now(timezone.utc),
    )
    session.add(prediction)
    session.commit()
    session.refresh(prediction)
    return prediction
