"""Metric computation and chart generation, kept separate from ml/train.py.

Separating "how good is this prediction set" (this module) from "how do we
produce a prediction set" (train.py's CV/tuning orchestration) means the
same metric and chart code can be reused for the CV-based metrics, the
temporal-holdout metrics, and later (Phase 5+) for monitoring live model
performance without duplicating logic.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: this runs in a training script, not a GUI session
import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_absolute_percentage_error,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.metrics import classification_report as sk_classification_report
from sklearn.metrics import r2_score, root_mean_squared_error

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGRAMS_DIR = REPO_ROOT / "docs" / "diagrams"

_MAX_JSON_POINTS = 300  # keep persisted plot data compact; PNGs carry the full picture


def _subsample(*arrays: np.ndarray, max_points: int = _MAX_JSON_POINTS, seed: int = 42) -> list[np.ndarray]:
    n = len(arrays[0])
    if n <= max_points:
        return list(arrays)
    rng = np.random.default_rng(seed)
    idx = rng.choice(n, size=max_points, replace=False)
    return [a[idx] for a in arrays]


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray) -> dict:
    """Full classification metric suite for a binary risk label (Section G)."""
    cm = confusion_matrix(y_true, y_pred)
    prob_true, prob_pred = calibration_curve(y_true, y_proba, n_bins=10, strategy="quantile")
    fpr, tpr, _ = roc_curve(y_true, y_proba)
    fpr_s, tpr_s = _subsample(fpr, tpr)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_weighted": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_proba)),
        "pr_auc": float(average_precision_score(y_true, y_proba)),
        "confusion_matrix": cm.tolist(),
        "per_class_report": sk_classification_report(y_true, y_pred, output_dict=True, zero_division=0),
        "calibration_curve": {"prob_true": prob_true.tolist(), "prob_pred": prob_pred.tolist()},
        "roc_curve": {"fpr": fpr_s.tolist(), "tpr": tpr_s.tolist()},
    }


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Full regression metric suite (Section G)."""
    residuals = y_true - y_pred
    # MAPE is undefined at y_true == 0; GPA/score targets are never exactly
    # zero in practice here, but guard anyway rather than raising.
    safe_mask = y_true != 0
    mape = float(mean_absolute_percentage_error(y_true[safe_mask], y_pred[safe_mask])) if safe_mask.any() else None

    y_true_s, y_pred_s, residuals_s = _subsample(y_true, y_pred, residuals)
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(root_mean_squared_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
        "mape": mape,
        "residual_plot_data": {"y_true": y_true_s.tolist(), "residual": residuals_s.tolist()},
        "predicted_vs_actual_data": {"y_true": y_true_s.tolist(), "y_pred": y_pred_s.tolist()},
    }


def save_comparison_chart(results: list[dict], task: str, metric_key: str, out_name: str) -> Path:
    """Bar chart comparing every algorithm on one metric for one task."""
    names = [r["algorithm"] for r in results]
    values = [r["cv_metrics"][metric_key] for r in results]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(names, values, color="#0F2038")
    best_idx = int(np.argmax(values))
    bars[best_idx].set_color("#D97706")
    ax.set_ylabel(metric_key)
    ax.set_title(f"{task}: {metric_key} by algorithm")
    ax.set_xticklabels(names, rotation=30, ha="right")
    fig.tight_layout()
    out_path = DIAGRAMS_DIR / out_name
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    return out_path


def save_confusion_matrix_chart(cm: list[list[int]], out_name: str) -> Path:
    cm_arr = np.array(cm)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    im = ax.imshow(cm_arr, cmap="Blues")
    labels = ["Not at risk", "At risk"]
    ax.set_xticks([0, 1], labels)
    ax.set_yticks([0, 1], labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    for i in range(cm_arr.shape[0]):
        for j in range(cm_arr.shape[1]):
            ax.text(j, i, str(cm_arr[i, j]), ha="center", va="center", color="black")
    fig.colorbar(im)
    fig.tight_layout()
    out_path = DIAGRAMS_DIR / out_name
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    return out_path


def save_roc_curve_chart(roc_curve_data: dict, out_name: str) -> Path:
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.plot(roc_curve_data["fpr"], roc_curve_data["tpr"], color="#0F2038")
    ax.plot([0, 1], [0, 1], linestyle="--", color="#94A3B8")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ROC curve")
    fig.tight_layout()
    out_path = DIAGRAMS_DIR / out_name
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    return out_path


def save_residual_chart(residual_plot_data: dict, out_name: str) -> Path:
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(residual_plot_data["y_true"], residual_plot_data["residual"], s=10, alpha=0.5, color="#0F2038")
    ax.axhline(0, color="#B91C1C", linestyle="--")
    ax.set_xlabel("Actual")
    ax.set_ylabel("Residual")
    ax.set_title("Residuals")
    fig.tight_layout()
    out_path = DIAGRAMS_DIR / out_name
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    return out_path


def save_scatter_chart(predicted_vs_actual_data: dict, out_name: str) -> Path:
    y_true = predicted_vs_actual_data["y_true"]
    y_pred = predicted_vs_actual_data["y_pred"]
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(y_true, y_pred, s=10, alpha=0.5, color="#0F2038")
    lo, hi = min(y_true + y_pred), max(y_true + y_pred)
    ax.plot([lo, hi], [lo, hi], linestyle="--", color="#D97706")
    ax.set_xlabel("Actual")
    ax.set_ylabel("Predicted")
    ax.set_title("Predicted vs actual")
    fig.tight_layout()
    out_path = DIAGRAMS_DIR / out_name
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    return out_path
