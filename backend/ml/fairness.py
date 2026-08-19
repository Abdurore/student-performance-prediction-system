"""Fairness audit across sensitive/grouping attributes (Section G).

Evaluated on the temporal holdout (train on earlier sessions, test on the
most recent) rather than in-sample predictions -- an in-sample audit would
use the same rows the model was fit on and could understate real
disparities. This reuses the exact split ml.train's temporal-holdout
metrics use, refitting the active model's own tuned hyperparameters
(model_registry.hyperparameters) fresh on the train side only.

gender is a protected attribute excluded from model *features*
(ml.config.USE_PROTECTED_ATTRIBUTES) but is legitimate -- expected, even
-- as a fairness *grouping* variable: Section G is explicit that protected
attributes are "used solely as grouping variables in the fairness audit."
entry_mode and accommodation are ordinary features audited here too,
since a model can discriminate on a sensitive axis via a correlated,
non-protected feature even when the protected column itself is excluded.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sqlmodel import Session, select

from app.db.session import engine
from app.models import ModelRegistry
from ml.config import TASK_KIND
from ml.features import build_course_score_features, build_semester_features, column_types
from ml.preprocessing import load_raw_tables
from ml.train import build_pipeline, temporal_holdout_indices

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
GROUP_COLUMNS: tuple[str, ...] = ("gender", "entry_mode", "accommodation")
DISPARITY_FLAG_THRESHOLD = 0.10  # 10 percentage points (Section G)


def _classification_group_metrics(y_true: np.ndarray, y_pred: np.ndarray, group_values: pd.Series) -> dict:
    report: dict[str, dict] = {}
    for group in sorted(group_values.dropna().unique().tolist()):
        mask = (group_values == group).to_numpy()
        yt, yp = y_true[mask], y_pred[mask]
        n = len(yt)
        if n == 0:
            continue
        tp = int(((yp == 1) & (yt == 1)).sum())
        fn = int(((yp == 0) & (yt == 1)).sum())
        fp = int(((yp == 1) & (yt == 0)).sum())
        tn = int(((yp == 0) & (yt == 0)).sum())
        report[str(group)] = {
            "n": n,
            "accuracy": float((yp == yt).mean()),
            "positive_prediction_rate": float(yp.mean()),
            "tpr": (tp / (tp + fn)) if (tp + fn) > 0 else None,
            "fpr": (fp / (fp + tn)) if (fp + tn) > 0 else None,
            "precision": (tp / (tp + fp)) if (tp + fp) > 0 else None,
        }
    return report


def _regression_group_metrics(y_true: np.ndarray, y_pred: np.ndarray, group_values: pd.Series, scale: float) -> dict:
    report: dict[str, dict] = {}
    for group in sorted(group_values.dropna().unique().tolist()):
        mask = (group_values == group).to_numpy()
        yt, yp = y_true[mask], y_pred[mask]
        n = len(yt)
        if n == 0:
            continue
        report[str(group)] = {
            "n": n,
            "mae": float(np.mean(np.abs(yt - yp))),
            "mean_predicted_normalised": float(np.mean(yp) / scale),
            "mean_actual_normalised": float(np.mean(yt) / scale),
        }
    return report


def _max_min_gap(per_group: dict, key: str) -> float | None:
    values = [g[key] for g in per_group.values() if g.get(key) is not None]
    if len(values) < 2:
        return None
    return max(values) - min(values)


def _flagged(gaps: dict[str, float | None]) -> bool:
    return any(gap is not None and gap > DISPARITY_FLAG_THRESHOLD for gap in gaps.values())


def _active_registry_row(task: str) -> ModelRegistry:
    with Session(engine) as db_session:
        registry_row = db_session.exec(
            select(ModelRegistry).where(ModelRegistry.task == task, ModelRegistry.is_active == True)  # noqa: E712
        ).first()
    if registry_row is None:
        raise ValueError(f"No active model registered for task '{task}'. Run `make train` first.")
    return registry_row


def _refit_on_temporal_train(task: str, X: pd.DataFrame, y: pd.Series, sessions: pd.Series):
    task_kind = TASK_KIND[task]
    numeric_cols, categorical_cols = column_types(X)
    registry_row = _active_registry_row(task)

    # use_smote isn't stored on ModelRegistry (only in the metrics JSON
    # train.py writes alongside it) -- read it from there so the temporal
    # refit uses the same pipeline shape the active model was chosen with.
    metrics_path = ARTIFACTS_DIR / "metrics" / f"{task}__{registry_row.algorithm}.json"
    use_smote = json.loads(metrics_path.read_text())["use_smote"] if metrics_path.exists() else False

    pipeline = build_pipeline(task_kind, registry_row.algorithm, numeric_cols, categorical_cols, use_smote)
    pipeline.set_params(**{k: v for k, v in registry_row.hyperparameters.items() if k in pipeline.get_params()})

    train_idx, test_idx = temporal_holdout_indices(sessions)
    pipeline.fit(X.iloc[train_idx], y.iloc[train_idx])
    return pipeline, train_idx, test_idx, registry_row.algorithm


def fairness_report(task: str) -> dict:
    """Compute the fairness audit for a task's active model on its temporal holdout."""
    task_kind = TASK_KIND[task]
    raw = load_raw_tables()
    students = raw["students"][["id", *GROUP_COLUMNS]].rename(columns={"id": "student_id"})

    if task == "course_score":
        X, y_df, meta = build_course_score_features(raw)
        y = y_df["target_total_score"]
        scale = 100.0
    else:
        X, y_df, meta = build_semester_features(raw)
        y = y_df["risk_label"] if task == "risk_classification" else y_df["target_gpa"]
        scale = 1.0 if task == "risk_classification" else 5.0

    sessions = meta["session"]
    pipeline, train_idx, test_idx, algorithm = _refit_on_temporal_train(task, X, y, sessions)

    X_test = X.iloc[test_idx]
    y_test = y.iloc[test_idx].to_numpy()
    groups_test = meta.iloc[test_idx].merge(students, on="student_id", how="left")

    if task_kind == "classification":
        proba = pipeline.predict_proba(X_test)[:, 1]
        y_pred = (proba >= 0.5).astype(int)
    else:
        y_pred = pipeline.predict(X_test)

    report: dict = {"task": task, "algorithm": algorithm, "n_test_rows": int(len(test_idx)), "groups": {}}
    for group_col in GROUP_COLUMNS:
        group_values = groups_test[group_col]
        if task_kind == "classification":
            per_group = _classification_group_metrics(y_test, y_pred, group_values)
            gaps = {
                "demographic_parity_difference": _max_min_gap(per_group, "positive_prediction_rate"),
                "equal_opportunity_difference": _max_min_gap(per_group, "tpr"),
                "predictive_parity_difference": _max_min_gap(per_group, "precision"),
            }
        else:
            per_group = _regression_group_metrics(y_test, y_pred, group_values, scale)
            gaps = {"demographic_parity_difference": _max_min_gap(per_group, "mean_predicted_normalised")}
        report["groups"][group_col] = {
            "per_group": per_group,
            **gaps,
            "flagged": _flagged(gaps),
        }
    report["any_group_flagged"] = any(g["flagged"] for g in report["groups"].values())
    return report


def _mirror_to_model_registry(task: str, report: dict) -> None:
    with Session(engine) as db_session:
        registry_row = db_session.exec(
            select(ModelRegistry).where(ModelRegistry.task == task, ModelRegistry.is_active == True)  # noqa: E712
        ).first()
        if registry_row is not None:
            registry_row.fairness_report = report
            db_session.add(registry_row)
            db_session.commit()


def save_fairness_report(task: str) -> Path:
    report = fairness_report(task)
    out_dir = ARTIFACTS_DIR / "fairness"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{task}_fairness.json"
    out_path.write_text(json.dumps(report, indent=2))
    _mirror_to_model_registry(task, report)
    return out_path


if __name__ == "__main__":
    for _task in TASK_KIND:
        path = save_fairness_report(_task)
        print(f"Wrote {path}")
