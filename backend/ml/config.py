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
