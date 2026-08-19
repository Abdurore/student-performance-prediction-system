"""ML pipeline configuration.

Only data-generation constants are populated in Phase 1. Feature lists and
hyperparameter grids are added in Phase 2/3 once feature engineering and
training begin -- keeping them out for now avoids the phase-gate violation
CLAUDE.md warns against (no ML logic ahead of its phase).
"""

from typing import Final

RANDOM_SEED: Final[int] = 42
N_STUDENTS: Final[int] = 1200
N_SESSIONS: Final[int] = 6
MISSINGNESS_RATE_RANGE: Final[tuple[float, float]] = (0.04, 0.08)
