"""Tests for Phase 4 SHAP explainability and the natural-language layer."""

import numpy as np
import pandas as pd
import pytest

from ml import explain as explain_module
from ml import preprocessing as preprocessing_module
from ml.explain import (
    FEATURE_METADATA,
    _format_value,
    explain_student,
    render_sentences,
    top_contributors,
)


def test_every_semester_feature_has_display_metadata(raw_tables) -> None:
    from ml.features import build_semester_features

    X, _y, _meta = build_semester_features(raw_tables)
    missing = [c for c in X.columns if c not in FEATURE_METADATA]
    assert missing == []


def test_every_course_score_feature_has_display_metadata(raw_tables) -> None:
    from ml.features import build_course_score_features

    X, _y, _meta = build_course_score_features(raw_tables)
    missing = [c for c in X.columns if c not in FEATURE_METADATA]
    assert missing == []


def test_top_contributors_ranks_by_magnitude() -> None:
    shap_row = np.array([0.01, -0.5, 0.2, -0.05, 0.3, 0.02])
    feature_values = pd.Series([1, 2, 3, 4, 5, 6], index=["a", "b", "c", "d", "e", "f"])
    contributors = top_contributors(shap_row, feature_values, top_n=3)
    assert [c["feature"] for c in contributors] == ["b", "e", "c"]
    assert [c["rank"] for c in contributors] == [1, 2, 3]


def test_render_sentences_matches_the_documented_style() -> None:
    contributors = [
        {"feature": "mean_attendance_rate", "shap_value": 0.23, "raw_value": 0.41, "rank": 1},
    ]
    sentences = render_sentences(contributors, "risk_classification")
    assert sentences == ["Attendance rate of 41% is the largest factor, increasing risk by 23 percentage points."]


def test_render_sentences_preserves_embedded_acronyms() -> None:
    """str.capitalize() would lowercase "GPA" in "recent GPA trend" -- guard against that."""
    contributors = [{"feature": "gpa_trend", "shap_value": -0.02, "raw_value": -0.5, "rank": 1}]
    sentences = render_sentences(contributors, "risk_classification")
    assert sentences[0].startswith("Recent GPA trend")


def test_render_sentences_singular_point_grammar() -> None:
    contributors = [{"feature": "prior_gpa", "shap_value": -1.0, "raw_value": 3.0, "rank": 1}]
    sentences = render_sentences(contributors, "gpa_regression")
    assert sentences[0].endswith("by 1.00 GPA point.")


@pytest.mark.parametrize(
    "unit,value,expected",
    [
        ("percent", 0.412, "41%"),
        ("gpa", 3.456, "3.46"),
        ("boolean", True, "yes"),
        ("categorical", "UTME", "UTME"),
        ("percent", None, "unknown"),
    ],
)
def test_format_value(unit, value, expected) -> None:
    assert _format_value(unit, value) == expected


@pytest.fixture()
def with_small_db(trained_registry, small_db_engine):
    """Point both explain.py's model lookup and preprocessing's raw-table
    loading at the isolated small test DB (and its pre-registered models)."""
    mp = pytest.MonkeyPatch()
    mp.setattr(explain_module, "engine", small_db_engine)
    mp.setattr(preprocessing_module, "engine", small_db_engine)
    yield
    mp.undo()


def test_explain_student_returns_five_ranked_readable_sentences(with_small_db) -> None:
    result = explain_student(1, "risk_classification")

    assert result["student_id"] == 1
    assert len(result["sentences"]) == 5
    assert len(result["contributors"]) == 5
    assert all(isinstance(s, str) and s.endswith(".") for s in result["sentences"])
    # ranked, most important first
    magnitudes = [abs(c["shap_value"]) for c in result["contributors"]]
    assert magnitudes == sorted(magnitudes, reverse=True)


def test_explain_student_works_for_gpa_regression_too(with_small_db) -> None:
    result = explain_student(2, "gpa_regression")
    assert len(result["sentences"]) == 5


def test_explain_student_rejects_course_score_task(with_small_db) -> None:
    with pytest.raises(ValueError, match="explain_enrolment"):
        explain_student(1, "course_score")


def test_explain_student_raises_for_unknown_student(with_small_db) -> None:
    with pytest.raises(ValueError, match="No feature rows"):
        explain_student(999_999, "risk_classification")
