"""SHAP explainability and the natural-language explanation layer (Section G).

Explanations are computed directly on the *original* feature columns
(before one-hot encoding), not the preprocessed matrix a model actually
sees. This is deliberate: every downstream consumer -- the natural
language sentences here, the SHAP waterfall the frontend will render in
Phase 7 -- needs to talk about "entry mode" or "attendance rate", not a
one-hot dummy column, and reasoning in the original space sidesteps
re-aggregating one-hot SHAP values back onto their parent feature.

The trick that makes this both correct and simple: `shap.Explainer` is
given the *pipeline's own* predict/predict_proba function as a plain
callable, wrapped only to round-trip categorical columns through integer
codes (SHAP's tabular masker requires a purely numeric array). Any
preprocessing the pipeline does internally -- imputation, scaling,
one-hot encoding -- is completely opaque to SHAP and does not need
special-casing per algorithm (TreeExplainer/LinearExplainer/etc), which
is what lets one implementation serve all six algorithms uniformly.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sqlmodel import Session, select

from app.db.session import engine
from app.models import ModelRegistry
from ml.config import TASK_KIND
from ml.features import build_course_score_features, build_semester_features, column_types
from ml.preprocessing import load_raw_tables

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
BACKGROUND_SAMPLE_SIZE = 100
TOP_N_CONTRIBUTORS = 5

# (display label, unit) for every feature across all three tasks. "Templates
# in one module, covering every feature" (Section G) is satisfied by this
# table plus the single generic renderer below, rather than 40 near-identical
# hand-written sentence templates -- the actual per-feature customisation
# (how a value and its effect are phrased) lives here, in one place.
FEATURE_METADATA: dict[str, tuple[str, str]] = {
    "prior_cgpa": ("prior CGPA", "gpa"),
    "prior_gpa": ("previous semester's GPA", "gpa"),
    "gpa_trend": ("recent GPA trend", "signed_gpa"),
    "gpa_volatility": ("GPA volatility", "gpa"),
    "credits_earned_ratio": ("credit completion rate", "percent"),
    "carryover_count": ("number of carryover courses", "count"),
    "semesters_completed": ("semesters completed", "count"),
    "ca_average": ("average continuous-assessment score", "score_30"),
    "ca_std_dev_across_courses": ("variability in continuous-assessment scores", "score_30"),
    "lowest_ca_score": ("lowest continuous-assessment score", "score_30"),
    "courses_below_ca_threshold": ("number of courses with weak continuous assessment", "count"),
    "mean_attendance_rate": ("attendance rate", "percent"),
    "min_attendance_rate": ("lowest course attendance rate", "percent"),
    "attendance_std_dev": ("variability in attendance across courses", "percent"),
    "courses_below_75_percent": ("number of courses with attendance below 75%", "count"),
    "credit_load": ("credit load", "units"),
    "core_course_ratio": ("share of courses that are core", "percent"),
    "mean_course_difficulty_index": ("average course difficulty", "generic"),
    "level": ("academic level", "level"),
    "ca_to_max_ratio": ("continuous-assessment score relative to the maximum", "percent"),
    "credit_load_vs_level_mean": ("credit load relative to peers at the same level", "units_signed"),
    "submission_rate": ("assignment submission rate", "percent"),
    "punctuality_rate": ("assignment submission punctuality", "percent"),
    "lms_logins_normalised": ("LMS login activity (relative to peers)", "zscore"),
    "study_hours_per_week": ("study hours per week", "hours"),
    "tutorial_attendance_rate": ("tutorial attendance rate", "percent"),
    "library_visits_normalised": ("library visit frequency (relative to peers)", "zscore"),
    "entry_mode": ("entry mode", "categorical"),
    "employment_status": ("employment status", "categorical"),
    "accommodation": ("accommodation type", "categorical"),
    "has_scholarship": ("scholarship status", "boolean"),
    "entry_score_normalised": ("entry score (relative to peers)", "zscore"),
    "attendance_x_ca_average": ("combined attendance and continuous-assessment performance", "generic"),
    "study_hours_per_credit_load": ("study hours per credit unit", "generic"),
    "gpa_trend_x_credit_load": ("GPA trend weighted by credit load", "generic"),
    "ca_score": ("continuous-assessment score", "score_30"),
    "attendance_rate": ("attendance rate", "percent"),
    "sessions_attended": ("class sessions attended", "count"),
    "sessions_held": ("class sessions held", "count"),
    "attendance_x_ca_score": ("combined attendance and continuous-assessment score", "generic"),
}

_ORDINALS = ("the largest factor", "the second-largest factor", "the third-largest factor",
             "the fourth-largest factor", "the fifth-largest factor")

_TASK_DIRECTION_WORDS: dict[str, tuple[str, str]] = {
    "risk_classification": ("increasing risk", "reducing risk"),
    "gpa_regression": ("raising the predicted GPA", "lowering the predicted GPA"),
    "course_score": ("raising the predicted score", "lowering the predicted score"),
}


def _format_value(unit: str, value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "unknown"
    if unit == "percent":
        return f"{float(value) * 100:.0f}%"
    if unit == "gpa":
        return f"{float(value):.2f}"
    if unit == "signed_gpa":
        return f"{float(value):+.2f}"
    if unit in ("score_30", "units", "count", "level", "units_signed"):
        return f"{float(value):.0f}" if unit != "units_signed" else f"{float(value):+.1f}"
    if unit == "hours":
        return f"{float(value):.1f} hrs/week"
    if unit == "zscore":
        return f"{float(value):+.2f} SD from average"
    if unit == "boolean":
        return "yes" if bool(value) else "no"
    if unit == "categorical":
        return str(value)
    return f"{float(value):.2f}"


def _load_active_pipeline(task: str) -> tuple[object, str]:
    """Load the joblib artifact for a task's currently-active model_registry row."""
    with Session(engine) as session:
        row = session.exec(
            select(ModelRegistry).where(ModelRegistry.task == task, ModelRegistry.is_active == True)  # noqa: E712
        ).first()
    if row is None:
        raise ValueError(f"No active model registered for task '{task}'. Run `make train` first.")
    pipeline = joblib.load(REPO_ROOT / row.artifact_path)
    return pipeline, row.algorithm


def _encode_categoricals(df: pd.DataFrame, categorical_cols: list[str], categories: dict[str, list]) -> pd.DataFrame:
    encoded = df.copy()
    for col in categorical_cols:
        mapping = {value: idx for idx, value in enumerate(categories[col])}
        encoded[col] = df[col].map(mapping).astype(float)
    return encoded


def _decode_categoricals(df: pd.DataFrame, categorical_cols: list[str], categories: dict[str, list]) -> pd.DataFrame:
    decoded = df.copy()
    for col in categorical_cols:
        cats = categories[col]
        idx = df[col].round().clip(0, len(cats) - 1).astype(int)
        decoded[col] = [cats[i] for i in idx]
    return decoded


def _make_predict_fn(pipeline, feature_names: list[str], numeric_cols: list[str],
                      categorical_cols: list[str], categories: dict[str, list], task_kind: str):
    def predict_fn(encoded_array: np.ndarray) -> np.ndarray:
        df = pd.DataFrame(encoded_array, columns=feature_names)
        decoded = _decode_categoricals(df, categorical_cols, categories)
        for col in numeric_cols:
            decoded[col] = decoded[col].astype(float)
        if task_kind == "classification":
            return pipeline.predict_proba(decoded)
        return pipeline.predict(decoded)

    return predict_fn


def compute_shap_values(
    pipeline, X_background: pd.DataFrame, X_explain: pd.DataFrame, task_kind: str
) -> np.ndarray:
    """SHAP values for X_explain's rows, in the *original* feature space.

    Returns an array of shape (n_rows, n_features). For classification the
    positive ("at risk") class is selected.
    """
    feature_names = list(X_background.columns)
    numeric_cols, categorical_cols = column_types(X_background)
    categories = {
        col: sorted(pd.concat([X_background[col], X_explain[col]]).dropna().unique().tolist())
        for col in categorical_cols
    }
    background_encoded = _encode_categoricals(X_background, categorical_cols, categories)
    explain_encoded = _encode_categoricals(X_explain, categorical_cols, categories)

    predict_fn = _make_predict_fn(pipeline, feature_names, numeric_cols, categorical_cols, categories, task_kind)
    masker = shap.maskers.Independent(background_encoded, max_samples=len(background_encoded))
    explainer = shap.Explainer(predict_fn, masker, feature_names=feature_names)
    explanation = explainer(explain_encoded, silent=True)

    values = explanation.values
    if task_kind == "classification":
        values = values[..., 1]
    return values


def top_contributors(
    shap_row: np.ndarray, feature_values: pd.Series, top_n: int = TOP_N_CONTRIBUTORS
) -> list[dict]:
    """Rank one row's SHAP values by magnitude and pair each with its raw value."""
    order = np.argsort(-np.abs(shap_row))[:top_n]
    feature_names = list(feature_values.index)
    contributors = []
    for rank, idx in enumerate(order):
        name = feature_names[idx]
        contributors.append(
            {
                "feature": name,
                "shap_value": float(shap_row[idx]),
                "raw_value": feature_values.iloc[idx],
                "rank": rank + 1,
            }
        )
    return contributors


def render_sentences(contributors: list[dict], task: str) -> list[str]:
    """Turn ranked SHAP contributors into readable sentences (Section G example format)."""
    increase_word, decrease_word = _TASK_DIRECTION_WORDS[task]
    sentences = []
    for contributor in contributors:
        name = contributor["feature"]
        label, unit = FEATURE_METADATA.get(name, (name.replace("_", " "), "generic"))
        formatted_value = _format_value(unit, contributor["raw_value"])
        ordinal = _ORDINALS[min(contributor["rank"] - 1, len(_ORDINALS) - 1)]
        shap_value = contributor["shap_value"]
        direction = increase_word if shap_value > 0 else decrease_word

        if task == "risk_classification":
            points = round(abs(shap_value) * 100)
            magnitude = f"{points:.0f} percentage point" + ("" if points == 1 else "s")
        elif task == "gpa_regression":
            points = round(abs(shap_value), 2)
            magnitude = f"{points:.2f} GPA point" + ("" if points == 1 else "s")
        else:
            points = round(abs(shap_value), 1)
            magnitude = f"{points:.1f} point" + ("" if points == 1 else "s")

        # Capitalize only the leading character -- str.capitalize() would
        # lowercase embedded acronyms like "GPA" or "CGPA" in labels such
        # as "prior CGPA" or "recent GPA trend".
        sentence_label = label[0].upper() + label[1:]
        sentences.append(f"{sentence_label} of {formatted_value} is {ordinal}, {direction} by {magnitude}.")
    return sentences


def _latest_row_for_student(X: pd.DataFrame, meta: pd.DataFrame, student_id: int) -> pd.Series:
    student_mask = meta["student_id"] == student_id
    if not student_mask.any():
        raise ValueError(f"No feature rows found for student_id={student_id}.")
    ordered = meta.loc[student_mask].assign(
        _year=lambda d: d["session"].str.slice(0, 4).astype(int),
        _sem=lambda d: d["semester"].astype(int),
    ).sort_values(["_year", "_sem"])
    return ordered.index[-1]


def explain_student(student_id: int, task: str = "risk_classification", top_n: int = TOP_N_CONTRIBUTORS) -> dict:
    """Explain one student's most recent semester prediction for T1/T2.

    Returns a dict with ranked contributors and their rendered sentences --
    the shape `predictions.feature_contributions` will store once the
    prediction API (Phase 5) starts calling this for real inference.
    """
    if task not in ("risk_classification", "gpa_regression"):
        raise ValueError("explain_student supports risk_classification and gpa_regression; see explain_enrolment for course_score.")

    task_kind = TASK_KIND[task]
    raw = load_raw_tables()
    X, _y, meta = build_semester_features(raw)
    row_index = _latest_row_for_student(X, meta, student_id)

    pipeline, algorithm = _load_active_pipeline(task)
    background = X.sample(n=min(BACKGROUND_SAMPLE_SIZE, len(X)), random_state=42)
    explain_row = X.loc[[row_index]]

    shap_values = compute_shap_values(pipeline, background, explain_row, task_kind)
    contributors = top_contributors(shap_values[0], explain_row.iloc[0], top_n)
    sentences = render_sentences(contributors, task)

    return {
        "student_id": student_id,
        "task": task,
        "algorithm": algorithm,
        "session": meta.loc[row_index, "session"],
        "semester": meta.loc[row_index, "semester"],
        "contributors": contributors,
        "sentences": sentences,
    }


def explain_enrolment(student_id: int, course_id: int, top_n: int = TOP_N_CONTRIBUTORS) -> dict:
    """Explain one student-course pair's course_score (T3) prediction."""
    raw = load_raw_tables()
    X, _y, meta = build_course_score_features(raw)
    mask = (meta["student_id"] == student_id) & (meta["course_id"] == course_id)
    if not mask.any():
        raise ValueError(f"No completed enrolment found for student_id={student_id}, course_id={course_id}.")
    row_index = meta.loc[mask].index[-1]

    pipeline, algorithm = _load_active_pipeline("course_score")
    background = X.sample(n=min(BACKGROUND_SAMPLE_SIZE, len(X)), random_state=42)
    explain_row = X.loc[[row_index]]

    shap_values = compute_shap_values(pipeline, background, explain_row, "regression")
    contributors = top_contributors(shap_values[0], explain_row.iloc[0], top_n)
    sentences = render_sentences(contributors, "course_score")

    return {
        "student_id": student_id,
        "course_id": course_id,
        "task": "course_score",
        "algorithm": algorithm,
        "contributors": contributors,
        "sentences": sentences,
    }


def global_feature_importance(task: str, sample_size: int = BACKGROUND_SAMPLE_SIZE) -> dict[str, float]:
    """Mean |SHAP value| per feature across a sample -- the "global SHAP summary" (Section G)."""
    task_kind = TASK_KIND[task]
    raw = load_raw_tables()
    if task == "course_score":
        X, _y, _meta = build_course_score_features(raw)
    else:
        X, _y, _meta = build_semester_features(raw)

    rng_sample = X.sample(n=min(sample_size, len(X)), random_state=42)
    background = X.sample(n=min(sample_size, len(X)), random_state=7)
    pipeline, _algorithm = _load_active_pipeline(task)

    shap_values = compute_shap_values(pipeline, background, rng_sample, task_kind)
    mean_abs = np.abs(shap_values).mean(axis=0)
    return dict(sorted(zip(X.columns, mean_abs.tolist()), key=lambda kv: -kv[1]))


def save_global_importance_chart(importance: dict[str, float], task: str, out_dir: Path | None = None) -> Path:
    """Horizontal bar chart of the top 15 features by mean |SHAP value| -- the
    "SHAP summary + feature-importance bar chart" Section G asks for globally."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from ml import evaluate

    out_dir = out_dir or evaluate.DIAGRAMS_DIR
    top = list(importance.items())[:15][::-1]
    labels = [FEATURE_METADATA.get(name, (name.replace("_", " "), ""))[0] for name, _ in top]
    values = [value for _, value in top]

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.barh(labels, values, color="#0F2038")
    ax.set_xlabel("Mean |SHAP value|")
    ax.set_title(f"{task}: global feature importance")
    fig.tight_layout()
    out_path = out_dir / f"{task}_shap_importance.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


def save_global_importance(task: str) -> tuple[Path, Path]:
    """Persist global feature importance for a task's active model as JSON + chart."""
    importance = global_feature_importance(task)
    out_dir = ARTIFACTS_DIR / "explanations"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{task}_global_importance.json"
    json_path.write_text(json.dumps(importance, indent=2))
    chart_path = save_global_importance_chart(importance, task)
    return json_path, chart_path


if __name__ == "__main__":
    for _task in TASK_KIND:
        json_path, chart_path = save_global_importance(_task)
        print(f"Wrote {json_path}")
        print(f"Wrote {chart_path}")
