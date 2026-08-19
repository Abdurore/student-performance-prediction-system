"""Tests for Phase 2 feature engineering and the leakage guard.

Runs against a small synthetic dataset loaded into an isolated temporary
database -- not the shared demo database -- so these tests are
self-contained and don't depend on `make seed` having been run first.
"""

import pytest

from ml.config import LEAKAGE_FORBIDDEN_COLUMNS
from ml.features import (
    LeakageError,
    assert_no_leakage,
    build_course_score_features,
    build_prediction_features,
    build_semester_features,
)


@pytest.fixture(scope="module")
def semester_features(raw_tables):
    return build_semester_features(raw_tables)


@pytest.fixture(scope="module")
def course_features(raw_tables):
    return build_course_score_features(raw_tables)


def test_semester_feature_table_has_at_least_25_features(semester_features) -> None:
    X, _y, _meta = semester_features
    assert X.shape[1] >= 25
    assert X.shape[0] > 0


def test_semester_features_pass_the_leakage_guard(semester_features) -> None:
    X, _y, _meta = semester_features
    assert_no_leakage(X, "risk_classification")
    assert_no_leakage(X, "gpa_regression")


def test_course_features_pass_the_leakage_guard(course_features) -> None:
    X, _y, _meta = course_features
    assert_no_leakage(X, "course_score")


@pytest.mark.parametrize("task", ["risk_classification", "gpa_regression"])
def test_leakage_guard_fails_loudly_when_a_banned_column_is_injected(semester_features, task) -> None:
    X, _y, _meta = semester_features
    for banned_column in LEAKAGE_FORBIDDEN_COLUMNS[task]:
        tainted = X.copy()
        tainted[banned_column] = 1.0
        with pytest.raises(LeakageError):
            assert_no_leakage(tainted, task)


def test_leakage_guard_fails_loudly_for_course_score_task(course_features) -> None:
    X, _y, _meta = course_features
    for banned_column in LEAKAGE_FORBIDDEN_COLUMNS["course_score"]:
        tainted = X.copy()
        tainted[banned_column] = 1.0
        with pytest.raises(LeakageError):
            assert_no_leakage(tainted, "course_score")


def test_leakage_guard_rejects_unknown_task(semester_features) -> None:
    X, _y, _meta = semester_features
    with pytest.raises(ValueError):
        assert_no_leakage(X, "not_a_real_task")


def test_course_score_features_are_restricted_to_ca_and_attendance(course_features) -> None:
    """Section G restricts T3 to CA/attendance-derived signals only."""
    X, _y, _meta = course_features
    allowed_terms = {"ca", "attendance", "session"}
    for column in X.columns:
        assert any(term in column for term in allowed_terms), column


def test_risk_label_matches_the_probation_threshold(semester_features) -> None:
    from app.core.academic_config import PROBATION_CGPA_THRESHOLD

    _X, y, _meta = semester_features
    assert set(y["risk_label"].unique()) <= {0, 1}
    assert (y.loc[y["risk_label"] == 1, "target_gpa"] < PROBATION_CGPA_THRESHOLD).all()
    assert (y.loc[y["risk_label"] == 0, "target_gpa"] >= PROBATION_CGPA_THRESHOLD).all()


def test_first_semester_students_have_no_prior_history_signal(semester_features) -> None:
    X, _y, meta = semester_features
    first_semester_mask = X["semesters_completed"] == 0
    assert first_semester_mask.any()
    assert X.loc[first_semester_mask, "prior_cgpa"].isna().all()


@pytest.fixture(scope="module")
def prediction_features(raw_tables):
    return build_prediction_features(raw_tables)


def test_prediction_features_same_columns_as_training(semester_features, prediction_features) -> None:
    X_train, _y, _meta = semester_features
    X_pred, meta_pred = prediction_features
    assert list(X_pred.columns) == list(X_train.columns)
    assert list(meta_pred.columns) == ["student_id", "session", "semester"]


def test_prediction_features_pass_the_leakage_guard(prediction_features) -> None:
    X_pred, _meta = prediction_features
    assert_no_leakage(X_pred, "risk_classification")
    assert_no_leakage(X_pred, "gpa_regression")


def test_prediction_features_one_row_per_active_student(raw_tables, prediction_features) -> None:
    _X_pred, meta_pred = prediction_features
    students = raw_tables["students"]
    active_ids = set(students.loc[students["is_active"].astype(bool), "id"])
    assert set(meta_pred["student_id"]) <= active_ids
    assert meta_pred["student_id"].is_unique
