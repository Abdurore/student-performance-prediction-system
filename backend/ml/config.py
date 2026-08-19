"""ML pipeline configuration.

Data-generation constants were added in Phase 1. Feature-engineering and
leakage-guard constants are added in Phase 2. Hyperparameter grids are
added in Phase 3 once training begins -- keeping them out for now avoids
the phase-gate violation CLAUDE.md warns against (no ML logic ahead of its
phase).
"""

from typing import Final

RANDOM_SEED: Final[int] = 42
N_STUDENTS: Final[int] = 1200
N_SESSIONS: Final[int] = 6
MISSINGNESS_RATE_RANGE: Final[tuple[float, float]] = (0.04, 0.08)

# Collected for the fairness audit (Phase 4) but excluded from model
# features by default -- flipping this is a defence-relevant, deliberate
# decision documented in docs/architecture.md, never a silent default.
USE_PROTECTED_ATTRIBUTES: Final[bool] = False
PROTECTED_ATTRIBUTES: Final[tuple[str, ...]] = ("gender", "state_of_origin", "date_of_birth")

# Section G's non-negotiable leakage guard: a target semester's own
# outcome fields may never be used to predict that same semester (T1/T2),
# and a target course's own outcome fields may never be used to predict
# that same course (T3). Prior-semester/prior-course values are fine and
# are exactly what the *_prior-prefixed features below carry instead.
LEAKAGE_FORBIDDEN_COLUMNS: Final[dict[str, frozenset[str]]] = {
    "risk_classification": frozenset({"exam_score", "total_score", "grade", "grade_point", "gpa", "cgpa"}),
    "gpa_regression": frozenset({"exam_score", "total_score", "grade", "grade_point", "gpa", "cgpa"}),
    "course_score": frozenset({"exam_score", "total_score"}),
}

# Accuracy/R^2 above these is treated as a leakage red flag (Section G).
LEAKAGE_ACCURACY_THRESHOLD: Final[float] = 0.96
LEAKAGE_R2_THRESHOLD: Final[float] = 0.95

# --- Phase 3: training ---

CV_FOLDS: Final[int] = 5
# T3 (course_score) is ~5x larger than T1/T2 and SVR/MLP scale poorly with
# sample count; fewer folds keeps `make train` runtime reasonable on a
# mid-range laptop (Section C) without changing what's compared -- every
# algorithm for a given task still sees the same fold count and splits.
CV_FOLDS_LARGE_TASK: Final[int] = 3
LARGE_TASK_ROW_THRESHOLD: Final[int] = 15_000

# How many of the most recent sessions form the temporal holdout's test
# side (Section G: "train on earlier sessions, test on the most recent").
TEMPORAL_HOLDOUT_SESSIONS: Final[int] = 1

TASK_KIND: Final[dict[str, str]] = {
    "risk_classification": "classification",
    "gpa_regression": "regression",
    "course_score": "regression",
}

# Small, defensible grids -- few enough combinations that `make train`
# finishes on a mid-range laptop, but every algorithm still gets genuine
# tuning rather than defaults. Logged in full alongside the winning
# parameters in each model's metrics JSON.
CLASSIFICATION_PARAM_GRIDS: Final[dict[str, dict]] = {
    "logistic_regression": {"model__C": [0.1, 1.0, 10.0]},
    "decision_tree": {"model__max_depth": [4, 8, None]},
    "random_forest": {"model__n_estimators": [150, 300], "model__max_depth": [8, None]},
    "xgboost": {"model__n_estimators": [150, 300], "model__max_depth": [3, 6]},
    "svm": {"model__C": [1.0, 10.0]},
    "mlp": {"model__hidden_layer_sizes": [(32,), (64, 32)], "model__alpha": [0.0001, 0.001]},
}
REGRESSION_PARAM_GRIDS: Final[dict[str, dict]] = {
    "linear_regression": {},
    "decision_tree": {"model__max_depth": [4, 8, None]},
    "random_forest": {"model__n_estimators": [150, 300], "model__max_depth": [8, None]},
    "xgboost": {"model__n_estimators": [150, 300], "model__max_depth": [3, 6]},
    "svm": {"model__C": [1.0, 10.0]},
    "mlp": {"model__hidden_layer_sizes": [(32,), (64, 32)], "model__alpha": [0.0001, 0.001]},
}
