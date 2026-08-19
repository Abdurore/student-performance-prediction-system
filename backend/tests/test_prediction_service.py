"""Unit tests for app.services.prediction_service, focused on the pieces
test_api_roles.py's permission-boundary tests don't exercise: the Section I
student-facing contributor filter, bulk/single-student inference, and the
small pure-math helpers around GPA projection and interval width.
"""

from sqlmodel import Session

from app.models.enums import UserRole
from app.services.prediction_service import (
    _active_model_rmse,
    _projected_cgpa,
    bulk_risk_scores,
    contributors_for_role,
    persist_prediction,
    predict_student_detail,
)
from app.models.enums import PredictionTask, RiskTier


def _fake_contributors(n: int) -> list[dict]:
    """Ranked contributors mixing fixed (prior_cgpa) and modifiable (attendance) features."""
    features = ["prior_cgpa", "mean_attendance_rate", "entry_score_normalised", "study_hours_per_week", "employment_status"]
    return [
        {"feature": features[i % len(features)], "rank": i + 1, "shap_value": 1.0 - i * 0.1, "raw_value": 0.5, "sentence": f"staff sentence {i}"}
        for i in range(n)
    ]


def test_contributors_for_role_staff_gets_unfiltered_top_n() -> None:
    contributors = _fake_contributors(10)
    top, sentences = contributors_for_role(contributors, "risk_classification", UserRole.ADMIN)
    assert len(top) == 5
    assert top[0]["feature"] == "prior_cgpa"  # fixed attribute allowed through for staff
    assert sentences == [c["sentence"] for c in top]


def test_contributors_for_role_student_excludes_fixed_attributes() -> None:
    contributors = _fake_contributors(10)
    top, sentences = contributors_for_role(contributors, "risk_classification", UserRole.STUDENT)
    assert all(c["feature"] not in ("prior_cgpa", "entry_score_normalised", "employment_status") for c in top)
    assert len(top) <= 5
    # forward-looking language, never a bare "predicted to fail"
    assert all("predicted to fail" not in s.lower() for s in sentences)


def test_contributors_for_role_student_view_does_not_mutate_staff_view() -> None:
    """Guards the Phase 5 bug where the student branch mutated the shared dict in place."""
    contributors = _fake_contributors(10)
    staff_top, _ = contributors_for_role(contributors, "risk_classification", UserRole.ADMIN)
    contributors_for_role(contributors, "risk_classification", UserRole.STUDENT)
    assert staff_top[0]["sentence"] == "staff sentence 0"


def test_projected_cgpa_blends_by_semesters_completed() -> None:
    # Halfway between a strong prior CGPA and a weak predicted GPA, weighted 3:1.
    projected = _projected_cgpa(predicted_gpa=2.0, prior_cgpa=4.0, semesters_completed=3)
    assert projected == (4.0 * 3 + 2.0) / 4


def test_projected_cgpa_falls_back_to_predicted_gpa_when_no_prior_history() -> None:
    assert _projected_cgpa(predicted_gpa=3.5, prior_cgpa=None, semesters_completed=0) == 3.5
    assert _projected_cgpa(predicted_gpa=3.5, prior_cgpa=3.0, semesters_completed=0) == 3.5


def test_active_model_rmse_falls_back_when_no_active_model(small_db_engine) -> None:
    with Session(small_db_engine) as session:
        assert _active_model_rmse(session, "gpa_regression") == 0.3


def test_bulk_risk_scores_returns_tiered_probabilities_for_every_ongoing_student(api_client, small_db_engine) -> None:
    scores = bulk_risk_scores()
    assert not scores.empty
    assert {"student_id", "probability", "risk_tier"}.issubset(scores.columns)
    assert scores["risk_tier"].isin(["low", "moderate", "high", "critical"]).all()
    assert scores["probability"].between(0, 1).all()


def test_bulk_risk_scores_can_be_filtered_to_specific_students(api_client) -> None:
    all_scores = bulk_risk_scores()
    some_ids = all_scores["student_id"].head(3).tolist()
    filtered = bulk_risk_scores(some_ids)
    assert set(filtered["student_id"]) == set(some_ids)


def test_predict_student_detail_returns_none_without_ongoing_enrolment(api_client) -> None:
    from ml.preprocessing import load_raw_tables

    ongoing_ids = set(bulk_risk_scores()["student_id"])
    all_ids = set(load_raw_tables()["students"]["id"])
    no_ongoing_ids = all_ids - ongoing_ids
    assert no_ongoing_ids, "fixture dataset should include at least one student with no ongoing enrolment"

    with Session(_engine_for(api_client)) as session:
        assert predict_student_detail(session, next(iter(no_ongoing_ids))) is None


def test_predict_student_detail_returns_full_prediction_for_ongoing_student(api_client) -> None:
    all_scores = bulk_risk_scores()
    student_id = int(all_scores["student_id"].iloc[0])
    with Session(_engine_for(api_client)) as session:
        result = predict_student_detail(session, student_id)
    assert result is not None
    assert result["student_id"] == student_id
    assert 0.0 <= result["risk"]["probability"] <= 1.0
    assert result["risk"]["risk_tier"] in ("low", "moderate", "high", "critical")
    assert 0.0 <= result["gpa"]["predicted_gpa"] <= 5.0
    assert len(result["risk"]["contributors"]) > 0
    assert len(result["gpa"]["contributors"]) > 0


def test_persist_prediction_writes_and_returns_the_row(api_client) -> None:
    all_scores = bulk_risk_scores()
    student_id = int(all_scores["student_id"].iloc[0])
    with Session(_engine_for(api_client)) as session:
        prediction = persist_prediction(
            session, student_id=student_id, task=PredictionTask.RISK_CLASSIFICATION,
            predicted_value=0.8, predicted_class="critical", risk_tier=RiskTier.CRITICAL,
            confidence=0.8, probability=0.8, feature_contributions=[{"feature": "x", "sentence": "y"}],
            input_snapshot={"session": "2024/2025", "semester": "1"}, model_version="test__v1",
        )
        assert prediction.id is not None
        assert prediction.student_id == student_id
        assert prediction.feature_contributions == {"contributors": [{"feature": "x", "sentence": "y"}]}


def _engine_for(api_client):
    from app.db import session as db_session_module

    return db_session_module.engine
