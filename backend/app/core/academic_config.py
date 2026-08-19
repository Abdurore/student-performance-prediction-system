"""Institution-specific academic rules used throughout the application."""

from typing import Final

GPA_SCALE: Final[float] = 5.0
CONTINUOUS_ASSESSMENT_WEIGHT: Final[int] = 30
EXAMINATION_WEIGHT: Final[int] = 70
PROBATION_CGPA_THRESHOLD: Final[float] = 2.0
LEVELS: Final[tuple[int, ...]] = (100, 200, 300, 400, 500)
SEMESTERS_PER_SESSION: Final[int] = 2
ENTRY_MODES: Final[tuple[str, ...]] = ("UTME", "Direct Entry", "Transfer")

GRADE_BANDS: Final[tuple[tuple[str, int, int, int], ...]] = (
    ("A", 70, 100, 5), ("B", 60, 69, 4), ("C", 50, 59, 3),
    ("D", 45, 49, 2), ("E", 40, 44, 1), ("F", 0, 39, 0),
)


def grade_for_score(score: float) -> tuple[str, int]:
    """Return the grade and grade point for a valid 0-100 assessment score.

    CA + exam totals are continuous (e.g. 39.5), so classification uses
    each band's lower bound as an inclusive floor and falls through to the
    next lower band otherwise -- checking the integer upper bound too would
    leave gaps between bands (e.g. 39.01-39.99 matched neither F's upper
    bound of 39 nor E's lower bound of 40).
    """
    if not 0 <= score <= 100:
        raise ValueError("Assessment scores must be between 0 and 100.")
    for grade, lower_bound, _upper_bound, grade_point in GRADE_BANDS:
        if score >= lower_bound:
            return grade, grade_point
    raise RuntimeError("Grade bands do not cover the configured score range.")
