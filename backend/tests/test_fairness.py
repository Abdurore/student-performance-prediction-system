"""Tests for Phase 4's fairness audit."""

import numpy as np
import pandas as pd
import pytest

from ml import fairness as fairness_module
from ml import preprocessing as preprocessing_module
from ml.fairness import (
    DISPARITY_FLAG_THRESHOLD,
    GROUP_COLUMNS,
    _classification_group_metrics,
    _flagged,
    _max_min_gap,
    _regression_group_metrics,
    fairness_report,
)


def test_classification_group_metrics_computes_expected_rates() -> None:
    y_true = np.array([1, 1, 0, 0, 1, 0])
    y_pred = np.array([1, 0, 0, 0, 1, 1])
    groups = pd.Series(["a", "a", "a", "b", "b", "b"])
    per_group = _classification_group_metrics(y_true, y_pred, groups)
    assert per_group["a"]["n"] == 3
    assert per_group["a"]["tpr"] == pytest.approx(0.5)  # 1 of 2 actual positives caught
    assert per_group["b"]["fpr"] == pytest.approx(0.5)  # 1 of 2 actual negatives misclassified


def test_regression_group_metrics_normalises_by_scale() -> None:
    y_true = np.array([4.0, 2.0])
    y_pred = np.array([5.0, 2.0])
    groups = pd.Series(["x", "y"])
    per_group = _regression_group_metrics(y_true, y_pred, groups, scale=5.0)
    assert per_group["x"]["mae"] == pytest.approx(1.0)
    assert per_group["x"]["mean_predicted_normalised"] == pytest.approx(1.0)
    assert per_group["y"]["mae"] == pytest.approx(0.0)


def test_max_min_gap_ignores_none_values() -> None:
    per_group = {"a": {"tpr": 0.8}, "b": {"tpr": None}, "c": {"tpr": 0.6}}
    assert _max_min_gap(per_group, "tpr") == pytest.approx(0.2)


def test_max_min_gap_requires_at_least_two_groups() -> None:
    assert _max_min_gap({"a": {"tpr": 0.8}}, "tpr") is None


def test_flagged_triggers_above_threshold() -> None:
    assert _flagged({"gap": DISPARITY_FLAG_THRESHOLD + 0.01}) is True
    assert _flagged({"gap": DISPARITY_FLAG_THRESHOLD}) is False
    assert _flagged({"gap": None}) is False


@pytest.fixture()
def with_small_db(trained_registry, small_db_engine):
    mp = pytest.MonkeyPatch()
    mp.setattr(fairness_module, "engine", small_db_engine)
    mp.setattr(preprocessing_module, "engine", small_db_engine)
    yield
    mp.undo()


def test_fairness_report_covers_every_group_column(with_small_db) -> None:
    report = fairness_report("risk_classification")
    assert set(report["groups"].keys()) == set(GROUP_COLUMNS)
    for group_col in GROUP_COLUMNS:
        entry = report["groups"][group_col]
        assert "demographic_parity_difference" in entry
        assert "flagged" in entry
        assert len(entry["per_group"]) >= 1
    assert isinstance(report["any_group_flagged"], bool)


def test_fairness_report_adapts_metrics_for_regression_tasks(with_small_db) -> None:
    report = fairness_report("gpa_regression")
    for group_col in GROUP_COLUMNS:
        entry = report["groups"][group_col]
        assert "demographic_parity_difference" in entry
        # regression tasks don't have TPR/equal-opportunity concepts
        assert "equal_opportunity_difference" not in entry
        for group_metrics in entry["per_group"].values():
            assert "mae" in group_metrics
