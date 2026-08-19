"""Train all six algorithms for all three tasks (Section G).

For each task:
1. Build features via ml.features and re-verify assert_no_leakage (a
   training run must never silently proceed on a leaked feature table,
   even though the builders already guarantee this -- defense in depth).
2. Tune each algorithm with GridSearchCV over one shared set of
   GroupKFold/StratifiedGroupKFold splits (grouped by student_id so a
   student's semesters never straddle train/test) -- the same splits for
   every algorithm in a task, so the six-way comparison is fair.
3. Compute the full metric suite via ml.evaluate on honest out-of-fold
   predictions (cross_val_predict with the tuned hyperparameters, not the
   grid search's internal averages), plus a temporal holdout (train on
   earlier sessions, test on the most recent one).
4. Flag -- never silently report -- any result over the leakage-warning
   thresholds (Section G).
5. Persist metrics JSON + PNG charts + a fitted joblib artifact per
   algorithm, and mirror the best-per-task model into model_registry.

Run standalone:

    python -m ml.train
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import GridSearchCV, GroupKFold, StratifiedGroupKFold, cross_val_predict
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.pipeline import Pipeline as SkPipeline
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sqlmodel import Session, select
from xgboost import XGBClassifier, XGBRegressor

from app.db.session import engine
from app.models import ModelRegistry
from ml import evaluate
from ml.config import (
    CLASSIFICATION_PARAM_GRIDS,
    CV_FOLDS,
    CV_FOLDS_LARGE_TASK,
    LARGE_TASK_ROW_THRESHOLD,
    LEAKAGE_ACCURACY_THRESHOLD,
    LEAKAGE_R2_THRESHOLD,
    RANDOM_SEED,
    REGRESSION_PARAM_GRIDS,
    TASK_KIND,
    TEMPORAL_HOLDOUT_SESSIONS,
)
from ml.features import assert_no_leakage, build_course_score_features, build_semester_features
from ml.preprocessing import build_preprocessing_pipeline, load_raw_tables

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
METRICS_DIR = ARTIFACTS_DIR / "metrics"
MODELS_DIR = ARTIFACTS_DIR / "models"

CLASSIFICATION_ALGORITHMS: dict[str, type] = {
    "logistic_regression": LogisticRegression,
    "decision_tree": DecisionTreeClassifier,
    "random_forest": RandomForestClassifier,
    "xgboost": XGBClassifier,
    "svm": SVC,
    "mlp": MLPClassifier,
}
REGRESSION_ALGORITHMS: dict[str, type] = {
    "linear_regression": LinearRegression,
    "decision_tree": DecisionTreeRegressor,
    "random_forest": RandomForestRegressor,
    "xgboost": XGBRegressor,
    "svm": SVR,
    "mlp": MLPRegressor,
}

_ALGORITHM_FIXED_KWARGS: dict[str, dict] = {
    "logistic_regression": {"max_iter": 2000, "random_state": RANDOM_SEED},
    "decision_tree": {"random_state": RANDOM_SEED},
    "random_forest": {"random_state": RANDOM_SEED, "n_jobs": -1},
    "xgboost": {"random_state": RANDOM_SEED, "n_jobs": -1, "eval_metric": "logloss"},
    "svm": {"probability": True, "random_state": RANDOM_SEED},
    "mlp": {"max_iter": 500, "random_state": RANDOM_SEED},
}

PRIMARY_METRIC: dict[str, str] = {
    "classification": "f1_macro",
    "regression": "r2",
}


def _build_estimator(task_kind: str, algo_key: str) -> object:
    cls = (CLASSIFICATION_ALGORITHMS if task_kind == "classification" else REGRESSION_ALGORITHMS)[algo_key]
    kwargs = dict(_ALGORITHM_FIXED_KWARGS.get(algo_key, {}))
    if algo_key == "svm" and task_kind == "regression":
        kwargs.pop("probability", None)
        kwargs.pop("random_state", None)
    return cls(**kwargs)


def _build_pipeline(
    task_kind: str, algo_key: str, numeric_cols: list[str], categorical_cols: list[str], use_smote: bool
) -> ImbPipeline | SkPipeline:
    """Build a fresh, unfitted pipeline -- called separately for CV tuning and the
    temporal refit so the two never share (and accidentally mutate) estimator state."""
    preprocessor = build_preprocessing_pipeline(numeric_cols, categorical_cols)
    estimator = _build_estimator(task_kind, algo_key)
    if use_smote:
        return ImbPipeline(
            steps=[
                ("preprocess", preprocessor),
                ("smote", SMOTE(random_state=RANDOM_SEED)),
                ("model", estimator),
            ]
        )
    return SkPipeline(steps=[("preprocess", preprocessor), ("model", estimator)])


def _column_types(X: pd.DataFrame) -> tuple[list[str], list[str]]:
    categorical = [c for c in X.columns if X[c].dtype == object]
    numeric = [c for c in X.columns if c not in categorical]
    return numeric, categorical


def _temporal_holdout_indices(sessions: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """Row indices for (train on earlier sessions, test on the most recent one(s))."""
    years = sessions.str.slice(0, 4).astype(int)
    cutoff = sorted(years.unique())[-TEMPORAL_HOLDOUT_SESSIONS]
    test_mask = years >= cutoff
    return np.flatnonzero(~test_mask.to_numpy()), np.flatnonzero(test_mask.to_numpy())


def _check_leakage_threshold(task_kind: str, metrics: dict) -> tuple[dict, bool]:
    """Redact and flag a metric set that crosses Section G's leakage-warning threshold."""
    if task_kind == "classification":
        flagged = metrics["accuracy"] > LEAKAGE_ACCURACY_THRESHOLD
        if flagged:
            print(
                f"    LEAKAGE WARNING: accuracy {metrics['accuracy']:.4f} exceeds "
                f"{LEAKAGE_ACCURACY_THRESHOLD} -- score withheld, investigate for leakage."
            )
    else:
        flagged = metrics["r2"] > LEAKAGE_R2_THRESHOLD
        if flagged:
            print(
                f"    LEAKAGE WARNING: R^2 {metrics['r2']:.4f} exceeds "
                f"{LEAKAGE_R2_THRESHOLD} -- score withheld, investigate for leakage."
            )
    if not flagged:
        return metrics, False
    redacted = {k: (None if isinstance(v, (int, float)) else v) for k, v in metrics.items()}
    redacted["leakage_flag"] = True
    return redacted, True


def _train_one_algorithm(
    task: str,
    task_kind: str,
    algo_key: str,
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    cv_splits: list[tuple[np.ndarray, np.ndarray]],
    temporal_idx: tuple[np.ndarray, np.ndarray],
    numeric_cols: list[str],
    categorical_cols: list[str],
    use_smote: bool,
    param_grid: dict,
) -> dict:
    pipeline = _build_pipeline(task_kind, algo_key, numeric_cols, categorical_cols, use_smote)

    scoring = "f1_macro" if task_kind == "classification" else "r2"
    started = time.perf_counter()
    search = GridSearchCV(pipeline, param_grid, cv=cv_splits, scoring=scoring, n_jobs=-1, refit=True)
    search.fit(X, y)
    duration_seconds = time.perf_counter() - started

    best_index = search.best_index_
    cv_mean = float(search.cv_results_["mean_test_score"][best_index])
    cv_std = float(search.cv_results_["std_test_score"][best_index])

    if task_kind == "classification":
        oof_proba = cross_val_predict(search.best_estimator_, X, y, cv=cv_splits, method="predict_proba")[:, 1]
        oof_pred = (oof_proba >= 0.5).astype(int)
        cv_metrics = evaluate.classification_metrics(y.to_numpy(), oof_pred, oof_proba)
    else:
        oof_pred = cross_val_predict(search.best_estimator_, X, y, cv=cv_splits, method="predict")
        cv_metrics = evaluate.regression_metrics(y.to_numpy(), oof_pred)
    cv_metrics, cv_leakage_flag = _check_leakage_threshold(task_kind, cv_metrics)

    # In-sample fit (deliberately trained and scored on the same data) to
    # report the train-vs-test gap, an overfitting indicator (Section G).
    in_sample_pipeline = search.best_estimator_
    if task_kind == "classification":
        train_score = float(np.mean(in_sample_pipeline.predict(X) == y.to_numpy()))
    else:
        train_score = float(in_sample_pipeline.score(X, y))
    train_test_gap = train_score - cv_mean

    # Temporal holdout: refit fresh on earlier sessions only, test on the most recent.
    train_idx, test_idx = temporal_idx
    temporal_pipeline = _build_pipeline(task_kind, algo_key, numeric_cols, categorical_cols, use_smote)
    temporal_pipeline.set_params(**search.best_params_)
    temporal_pipeline.fit(X.iloc[train_idx], y.iloc[train_idx])
    if task_kind == "classification":
        temporal_proba = temporal_pipeline.predict_proba(X.iloc[test_idx])[:, 1]
        temporal_pred = (temporal_proba >= 0.5).astype(int)
        temporal_metrics = evaluate.classification_metrics(
            y.iloc[test_idx].to_numpy(), temporal_pred, temporal_proba
        )
    else:
        temporal_pred = temporal_pipeline.predict(X.iloc[test_idx])
        temporal_metrics = evaluate.regression_metrics(y.iloc[test_idx].to_numpy(), temporal_pred)
    temporal_metrics, temporal_leakage_flag = _check_leakage_threshold(task_kind, temporal_metrics)

    return {
        "algorithm": algo_key,
        "task": task,
        "use_smote": use_smote,
        "best_params": search.best_params_,
        "cv_mean": cv_mean,
        "cv_std": cv_std,
        "cv_metrics": cv_metrics,
        "temporal_holdout_metrics": temporal_metrics,
        "train_score": train_score,
        "train_test_gap": train_test_gap,
        "training_duration_seconds": duration_seconds,
        "leakage_flag": cv_leakage_flag or temporal_leakage_flag,
        "fitted_pipeline": search.best_estimator_,
        "n_rows": len(X),
        "feature_columns": list(X.columns),
    }


def train_task(task: str) -> list[dict]:
    task_kind = TASK_KIND[task]
    print(f"\n=== Training task: {task} ({task_kind}) ===")
    raw = load_raw_tables()

    if task == "course_score":
        X, y_df, meta = build_course_score_features(raw)
        y = y_df["target_total_score"]
    else:
        X, y_df, meta = build_semester_features(raw)
        y = y_df["risk_label"] if task == "risk_classification" else y_df["target_gpa"]

    assert_no_leakage(X, task)
    numeric_cols, categorical_cols = _column_types(X)
    groups = meta["student_id"]
    sessions = meta["session"]

    n_splits = CV_FOLDS_LARGE_TASK if len(X) >= LARGE_TASK_ROW_THRESHOLD else CV_FOLDS
    if task_kind == "classification":
        cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_SEED)
    else:
        cv = GroupKFold(n_splits=n_splits)
    cv_splits = list(cv.split(X, y, groups))
    temporal_idx = _temporal_holdout_indices(sessions)

    grids = dict(CLASSIFICATION_PARAM_GRIDS if task_kind == "classification" else REGRESSION_PARAM_GRIDS)
    if len(X) >= LARGE_TASK_ROW_THRESHOLD and "svm" in grids:
        # SVR/SVC scale poorly with sample count (~25s/fit at this row count vs
        # <1s for the tree-based algorithms) -- one C value keeps `make train`
        # tractable on a mid-range laptop without dropping SVM from the comparison.
        grids["svm"] = {"model__C": [1.0]}
    algorithms = CLASSIFICATION_ALGORITHMS if task_kind == "classification" else REGRESSION_ALGORITHMS
    smote_variants = [True, False] if task_kind == "classification" else [False]

    results: list[dict] = []
    for algo_key in algorithms:
        for use_smote in smote_variants:
            label = f"{algo_key}{' + SMOTE' if use_smote else ''}"
            print(f"  Training {label}...")
            result = _train_one_algorithm(
                task, task_kind, algo_key, X, y, groups, cv_splits, temporal_idx,
                numeric_cols, categorical_cols, use_smote, grids[algo_key],
            )
            results.append(result)
            primary = PRIMARY_METRIC[task_kind]
            score = result["cv_metrics"].get(primary)
            score_str = f"{score:.4f}" if score is not None else "WITHHELD (leakage flag)"
            print(f"    {primary}={score_str}  duration={result['training_duration_seconds']:.1f}s")

    return results


def _select_primary_result(results: list[dict], task_kind: str) -> dict:
    """For a task, keep one result per algorithm (the better SMOTE variant if applicable)."""
    by_algo: dict[str, dict] = {}
    for r in results:
        key = r["algorithm"]
        primary = PRIMARY_METRIC[task_kind]
        current = by_algo.get(key)
        score = r["cv_metrics"].get(primary) or -np.inf
        current_score = (current["cv_metrics"].get(primary) if current else None) or -np.inf
        if current is None or score > current_score:
            by_algo[key] = r
    return by_algo


def persist_task_results(task: str, results: list[dict]) -> list[dict]:
    """Write metrics JSON, PNG charts, joblib artifacts, and model_registry rows."""
    task_kind = TASK_KIND[task]
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    primary_by_algo = _select_primary_result(results, task_kind)
    trained_at = datetime.now(timezone.utc)
    persisted_summaries: list[dict] = []

    for algo_key, result in primary_by_algo.items():
        version = f"{task}__{algo_key}"
        artifact_path = MODELS_DIR / f"{version}.joblib"
        joblib.dump(result["fitted_pipeline"], artifact_path)

        metrics_payload = {
            "version": version,
            "task": task,
            "algorithm": algo_key,
            "use_smote": result["use_smote"],
            "best_params": result["best_params"],
            "cv_mean": result["cv_mean"],
            "cv_std": result["cv_std"],
            "cv_metrics": result["cv_metrics"],
            "temporal_holdout_metrics": result["temporal_holdout_metrics"],
            "train_score": result["train_score"],
            "train_test_gap": result["train_test_gap"],
            "training_duration_seconds": result["training_duration_seconds"],
            "leakage_flag": result["leakage_flag"],
            "trained_at": trained_at.isoformat(),
        }
        (METRICS_DIR / f"{version}.json").write_text(json.dumps(metrics_payload, indent=2))
        persisted_summaries.append(metrics_payload)

    # comparison chart across all algorithms for this task
    comparable = [r for r in primary_by_algo.values() if not r["leakage_flag"]]
    if comparable:
        evaluate.save_comparison_chart(comparable, task, PRIMARY_METRIC[task_kind], f"{task}_comparison.png")

    best = max(comparable, key=lambda r: r["cv_metrics"][PRIMARY_METRIC[task_kind]], default=None)
    if best is not None:
        if task_kind == "classification":
            evaluate.save_confusion_matrix_chart(best["cv_metrics"]["confusion_matrix"], f"{task}_confusion_matrix.png")
            evaluate.save_roc_curve_chart(best["cv_metrics"]["roc_curve"], f"{task}_roc_curve.png")
        else:
            evaluate.save_residual_chart(best["cv_metrics"]["residual_plot_data"], f"{task}_residuals.png")
            evaluate.save_scatter_chart(best["cv_metrics"]["predicted_vs_actual_data"], f"{task}_predicted_vs_actual.png")

    _mirror_to_model_registry(primary_by_algo, best_algo=best["algorithm"] if best else None)
    return persisted_summaries


def _mirror_to_model_registry(primary_by_algo: dict[str, dict], best_algo: str | None) -> None:
    """Insert/replace this run's rows -- re-running `make train` must stay idempotent
    rather than tripping model_registry.version's unique constraint."""
    with Session(engine) as session:
        versions = [f"{result['task']}__{algo_key}" for algo_key, result in primary_by_algo.items()]
        existing = session.exec(select(ModelRegistry).where(ModelRegistry.version.in_(versions))).all()
        for row in existing:
            session.delete(row)
        session.commit()

        for algo_key, result in primary_by_algo.items():
            version = f"{result['task']}__{algo_key}"
            registry_row = ModelRegistry(
                version=version,
                task=result["task"],
                algorithm=algo_key,
                trained_at=datetime.now(timezone.utc),
                training_rows=result["n_rows"],
                feature_list=result["feature_columns"],
                hyperparameters=result["best_params"],
                metrics=result["cv_metrics"],
                fairness_report=None,
                artifact_path=str((MODELS_DIR / f"{version}.joblib").relative_to(REPO_ROOT)),
                is_active=(algo_key == best_algo),
            )
            session.add(registry_row)
        session.commit()


def print_comparison_table(task: str, results: list[dict]) -> None:
    task_kind = TASK_KIND[task]
    primary = PRIMARY_METRIC[task_kind]
    primary_by_algo = _select_primary_result(results, task_kind)
    print(f"\n--- {task} comparison ({primary}) ---")
    header = f"{'algorithm':<20}{'smote':<8}{primary:<12}{'cv_std':<10}{'train_gap':<12}{'seconds':<10}"
    print(header)
    for algo_key, r in sorted(primary_by_algo.items(), key=lambda kv: -(kv[1]["cv_metrics"].get(primary) or -1)):
        score = r["cv_metrics"].get(primary)
        score_str = f"{score:.4f}" if score is not None else "WITHHELD"
        print(
            f"{algo_key:<20}{str(r['use_smote']):<8}{score_str:<12}{r['cv_std']:<10.4f}"
            f"{r['train_test_gap']:<12.4f}{r['training_duration_seconds']:<10.1f}"
        )


def main() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    all_results: dict[str, list[dict]] = {}
    for task in TASK_KIND:
        results = train_task(task)
        persist_task_results(task, results)
        print_comparison_table(task, results)
        all_results[task] = results

    any_flagged = any(r["leakage_flag"] for results in all_results.values() for r in results)
    if any_flagged:
        print("\nOne or more models were flagged for the leakage-warning threshold -- see warnings above.")


if __name__ == "__main__":
    main()
