"""Tests for Phase 3 training: the leakage-threshold guard, temporal-holdout
splitting, and a fast end-to-end run of train_task on a small dataset.

Full grids/fold counts would take minutes per algorithm (see ml/train.py's
docstring); these tests monkeypatch tiny grids and fold counts so the
suite stays fast while still exercising the real training/persistence path.
"""

import json

import pandas as pd
import pytest
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.pipeline import Pipeline as SkPipeline
from sqlmodel import Session, select

from app.models import ModelRegistry
from ml import train as train_module
from ml.train import (
    _build_pipeline,
    _check_leakage_threshold,
    _temporal_holdout_indices,
    persist_task_results,
    train_task,
)


def test_temporal_holdout_splits_on_the_most_recent_session() -> None:
    sessions = pd.Series(
        ["2019/2020", "2019/2020", "2020/2021", "2021/2022", "2021/2022"]
    )
    train_idx, test_idx = _temporal_holdout_indices(sessions)
    assert set(train_idx) == {0, 1, 2}
    assert set(test_idx) == {3, 4}


def test_build_pipeline_uses_smote_only_when_requested() -> None:
    with_smote = _build_pipeline("classification", "logistic_regression", ["a"], [], use_smote=True)
    without_smote = _build_pipeline("classification", "logistic_regression", ["a"], [], use_smote=False)
    assert isinstance(with_smote, ImbPipeline)
    assert "smote" in dict(with_smote.steps)
    assert isinstance(without_smote, SkPipeline)
    assert "smote" not in dict(without_smote.steps)


def test_leakage_threshold_passes_through_realistic_classification_metrics() -> None:
    metrics = {"accuracy": 0.87, "f1_macro": 0.85}
    result, flagged = _check_leakage_threshold("classification", metrics)
    assert flagged is False
    assert result == metrics


def test_leakage_threshold_redacts_and_flags_suspicious_classification_metrics() -> None:
    metrics = {"accuracy": 0.995, "f1_macro": 0.99, "confusion_matrix": [[1, 0], [0, 1]]}
    result, flagged = _check_leakage_threshold("classification", metrics)
    assert flagged is True
    assert result["leakage_flag"] is True
    assert result["accuracy"] is None
    assert result["f1_macro"] is None
    # Non-numeric fields (e.g. the confusion matrix) are left alone, not nulled.
    assert result["confusion_matrix"] == [[1, 0], [0, 1]]


def test_leakage_threshold_redacts_suspicious_regression_metrics() -> None:
    metrics = {"r2": 0.97, "mae": 0.1}
    result, flagged = _check_leakage_threshold("regression", metrics)
    assert flagged is True
    assert result["r2"] is None


@pytest.fixture(scope="module")
def tiny_grids():
    """Monkeypatch every grid down to one combination and CV to 2 folds for speed."""
    mp = pytest.MonkeyPatch()
    mp.setattr(train_module, "CLASSIFICATION_PARAM_GRIDS", {
        "logistic_regression": {"model__C": [1.0]},
        "decision_tree": {"model__max_depth": [4]},
        "random_forest": {"model__n_estimators": [50]},
        "xgboost": {"model__n_estimators": [50]},
        "svm": {"model__C": [1.0]},
        "mlp": {"model__hidden_layer_sizes": [(8,)]},
    })
    mp.setattr(train_module, "REGRESSION_PARAM_GRIDS", {
        "linear_regression": {},
        "decision_tree": {"model__max_depth": [4]},
        "random_forest": {"model__n_estimators": [50]},
        "xgboost": {"model__n_estimators": [50]},
        "svm": {"model__C": [1.0]},
        "mlp": {"model__hidden_layer_sizes": [(8,)]},
    })
    mp.setattr(train_module, "CV_FOLDS", 2)
    mp.setattr(train_module, "CV_FOLDS_LARGE_TASK", 2)
    yield
    mp.undo()


@pytest.fixture(scope="module")
def risk_classification_results(raw_tables, tiny_grids):
    X, y_df, meta = train_module.build_semester_features(raw_tables)
    train_module.assert_no_leakage(X, "risk_classification")
    return train_task("risk_classification")


def test_train_task_returns_a_result_per_algorithm_and_smote_variant(risk_classification_results) -> None:
    results = risk_classification_results
    assert len(results) == 12  # 6 algorithms x {with, without} SMOTE
    algos = {r["algorithm"] for r in results}
    assert algos == {"logistic_regression", "decision_tree", "random_forest", "xgboost", "svm", "mlp"}


def test_train_task_results_are_not_leakage_flagged_on_real_data(risk_classification_results) -> None:
    assert all(not r["leakage_flag"] for r in risk_classification_results)
    assert all(0.0 <= r["cv_metrics"]["accuracy"] <= 1.0 for r in risk_classification_results)


def test_persist_task_results_writes_metrics_and_is_idempotent(
    tmp_path, small_db_engine, risk_classification_results
) -> None:
    mp = pytest.MonkeyPatch()
    mp.setattr(train_module, "METRICS_DIR", tmp_path / "metrics")
    mp.setattr(train_module, "MODELS_DIR", tmp_path / "models")
    mp.setattr(train_module, "CHARTS_DIR", tmp_path / "charts")
    mp.setattr(train_module, "engine", small_db_engine)
    try:
        persist_task_results("risk_classification", risk_classification_results)
        metrics_files = list((tmp_path / "metrics").glob("risk_classification__*.json"))
        assert len(metrics_files) == 6  # one surviving (better-SMOTE-variant) result per algorithm

        payload = json.loads(metrics_files[0].read_text())
        assert "cv_metrics" in payload
        assert "temporal_holdout_metrics" in payload
        assert "best_params" in payload

        with Session(small_db_engine) as session:
            rows = session.exec(
                select(ModelRegistry).where(ModelRegistry.task == "risk_classification")
            ).all()
        assert len(rows) == 6
        assert sum(row.is_active for row in rows) == 1

        # Re-running must not violate model_registry.version's unique constraint.
        persist_task_results("risk_classification", risk_classification_results)
        with Session(small_db_engine) as session:
            rows_after = session.exec(
                select(ModelRegistry).where(ModelRegistry.task == "risk_classification")
            ).all()
        assert len(rows_after) == 6
    finally:
        mp.undo()
