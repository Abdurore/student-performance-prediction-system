"""Unit tests for app.services.analytics_service: every figure computed
live from the DB and active models, never a precomputed snapshot."""

from sqlmodel import Session

from app.services.analytics_service import (
    get_attendance_performance,
    get_correlations,
    get_course_difficulty,
    get_gpa_distribution,
    get_level_comparison,
    get_overview,
    get_trends,
)


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


def test_get_gpa_distribution_bucket_counts_sum_to_student_count(small_db_engine) -> None:
    with Session(small_db_engine) as session:
        distribution = get_gpa_distribution(session)
    assert distribution.n_students > 0
    assert sum(b.count for b in distribution.buckets) == distribution.n_students
    # Ten contiguous 0.5-wide buckets covering the full [0, 5.0] GPA scale.
    assert len(distribution.buckets) == 10
    assert distribution.buckets[0].range_low == 0.0
    assert distribution.buckets[-1].range_high == 5.0
    for a, b in zip(distribution.buckets, distribution.buckets[1:]):
        assert a.range_high == b.range_low


def test_get_attendance_performance_regression_line_is_computed_from_full_data(small_db_engine) -> None:
    with Session(small_db_engine) as session:
        result = get_attendance_performance(session)
    assert result.n_total > 0
    assert result.n_sampled <= result.n_total
    assert result.n_sampled == len(result.points)
    for point in result.points:
        assert 0.0 <= point.attendance_rate <= 1.0
        assert 0.0 <= point.total_score <= 100.0

    # The fitted line should roughly agree with a from-scratch numpy fit
    # over the *sampled* points -- not identical (the line is fit on the
    # full population, not the sample) but the same general trend.
    import numpy as np

    xs = [p.attendance_rate for p in result.points]
    ys = [p.total_score for p in result.points]
    sample_slope, _sample_intercept = np.polyfit(xs, ys, deg=1)
    assert (result.slope > 0) == (sample_slope > 0)


def test_get_level_comparison_covers_every_seeded_level(small_db_engine) -> None:
    with Session(small_db_engine) as session:
        comparison = get_level_comparison(session)
    assert len(comparison.levels) > 0
    total_students = sum(item.n_students for item in comparison.levels)
    with Session(small_db_engine) as session:
        from sqlmodel import select

        from app.models import Student

        seeded_total = len(session.exec(select(Student.id)).all())
    assert total_students == seeded_total
    for item in comparison.levels:
        assert 100 <= item.level <= 500
        assert 0.0 <= item.average_gpa <= 5.0
        tier_total = item.at_risk_low + item.at_risk_moderate + item.at_risk_high + item.at_risk_critical
        assert tier_total <= item.n_students
