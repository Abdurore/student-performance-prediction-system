"""Tests for the Phase 1 synthetic data generator.

The full dataset is generated once per module (it takes several seconds
for 1,200 students) and reused across assertions.
"""

import pytest

from app.core.academic_config import grade_for_score
from ml import config
from ml.data_generator import calibration_report, generate_dataset


@pytest.fixture(scope="module")
def dataset():
    return generate_dataset()


def test_row_counts_match_configured_size(dataset) -> None:
    assert dataset["students"].shape[0] == config.N_STUDENTS
    assert dataset["enrolments"].shape[0] > 0
    # staff (admin + lecturers + advisers) plus one account per student
    assert dataset["users"].shape[0] > config.N_STUDENTS


def test_ongoing_enrolments_have_no_target_semester_fields(dataset) -> None:
    """The current, not-yet-graded semester must not leak its own outcome."""
    enrolments = dataset["enrolments"]
    ongoing = enrolments[enrolments["status"] == "ongoing"]
    assert len(ongoing) > 0
    assert ongoing["exam_score"].isna().all()
    assert ongoing["total_score"].isna().all()
    assert ongoing["grade"].isna().all()
    assert ongoing["grade_point"].isna().all()
    completed = enrolments[enrolments["status"] == "completed"]
    assert completed["total_score"].notna().all()


def test_missingness_within_target_range(dataset) -> None:
    low, high = config.MISSINGNESS_RATE_RANGE
    tolerance = 0.02
    for col in ["sessions_held", "sessions_attended", "attendance_rate"]:
        rate = dataset["attendance"][col].isna().mean()
        assert low - tolerance <= rate <= high + tolerance, f"{col} missingness {rate}"

    engagement_cols = [
        "assignments_submitted", "assignments_total", "submission_punctuality_rate",
        "lms_logins", "library_visits", "study_hours_per_week",
        "tutorial_attendance", "extracurricular_hours",
    ]
    for col in engagement_cols:
        rate = dataset["engagement"][col].isna().mean()
        assert low - tolerance <= rate <= high + tolerance, f"{col} missingness {rate}"


def test_correlations_are_in_the_documented_ballpark(dataset) -> None:
    """Loose bounds around the spec's approximate (r ~=) targets."""
    report = calibration_report(dataset)
    assert 0.4 <= report["correlation_attendance_vs_ca_score"] <= 0.8
    assert 0.3 <= report["correlation_attendance_vs_total_score"] <= 0.7
    assert 0.45 <= report["correlation_prior_cgpa_vs_next_gpa"] <= 0.85


def test_generation_is_reproducible_for_a_fixed_seed(monkeypatch) -> None:
    monkeypatch.setattr("ml.data_generator.N_STUDENTS", 60)
    first = generate_dataset(seed=123)
    second = generate_dataset(seed=123)
    assert first["students"]["matric_no"].tolist() == second["students"]["matric_no"].tolist()
    assert (
        first["enrolments"]["total_score"].fillna(-1).tolist()
        == second["enrolments"]["total_score"].fillna(-1).tolist()
    )


def test_grade_bands_cover_every_half_point_score() -> None:
    """Regression test for the boundary gap fixed in academic_config.grade_for_score."""
    for tenths in range(0, 1001):
        score = tenths / 10
        grade, points = grade_for_score(score)
        assert grade in {"A", "B", "C", "D", "E", "F"}
        assert 0 <= points <= 5


def test_grade_for_score_rejects_out_of_range_values() -> None:
    with pytest.raises(ValueError):
        grade_for_score(-1)
    with pytest.raises(ValueError):
        grade_for_score(100.1)
