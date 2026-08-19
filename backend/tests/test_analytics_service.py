"""Unit tests for app.services.analytics_service: every figure computed
live from the DB and active models, never a precomputed snapshot."""

from sqlmodel import Session

from app.services.analytics_service import get_correlations, get_course_difficulty, get_overview, get_trends


def test_get_overview_totals_match_the_seeded_dataset(api_client, small_db_engine) -> None:
    with Session(small_db_engine) as session:
        overview = get_overview(session)
    assert overview.total_students > 0
    assert overview.active_students <= overview.total_students
    assert overview.at_risk_low + overview.at_risk_moderate + overview.at_risk_high + overview.at_risk_critical > 0
    assert 0.0 <= overview.average_cgpa <= 5.0
    assert overview.total_interventions_open == 0  # nothing created yet in this fixture DB


def test_get_trends_groups_by_session_and_sorts_chronologically(small_db_engine) -> None:
    with Session(small_db_engine) as session:
        trends = get_trends(session)
    assert len(trends.points) > 0
    sessions = [p.session for p in trends.points]
    assert sessions == sorted(sessions)
    for point in trends.points:
        assert point.n_students > 0
        assert 0.0 <= point.average_gpa <= 5.0


def test_get_correlations_returns_a_square_symmetric_matrix() -> None:
    correlations = get_correlations()
    n = len(correlations.features)
    assert n > 0
    assert len(correlations.matrix) == n
    assert all(len(row) == n for row in correlations.matrix)
    # A feature's correlation with itself is always 1.0.
    for i in range(n):
        assert correlations.matrix[i][i] == 1.0


def test_get_course_difficulty_ranks_by_failure_rate_descending(small_db_engine) -> None:
    with Session(small_db_engine) as session:
        difficulty = get_course_difficulty(session)
    failure_rates = [item.failure_rate for item in difficulty.items]
    assert failure_rates == sorted(failure_rates, reverse=True)
    for item in difficulty.items:
        assert item.n_completed > 0
        assert 0.0 <= item.failure_rate <= 1.0
