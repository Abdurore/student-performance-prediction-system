"""Feature engineering and the data-leakage guard.

Two feature tables are built, at two different grains, because Section G
scopes them differently:

- T1 (risk classification) and T2 (GPA regression) share one table at the
  (student, session, semester) grain -- "will/what will this semester's
  outcome be, using only what was knowable *during* that semester".
- T3 (course score regression) gets its own, deliberately narrow table at
  the (student, course, session, semester) grain, restricted to CA and
  attendance per the spec ("...from CA and attendance only").

Every function that returns a feature table returns features and labels
as *separate* DataFrames -- labels are never mixed into the columns
assert_no_leakage checks, because the label itself (e.g. that semester's
gpa) would trivially trip the guard despite being the prediction target,
not a leaked input.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.academic_config import CONTINUOUS_ASSESSMENT_WEIGHT, PROBATION_CGPA_THRESHOLD
from ml.config import LEAKAGE_FORBIDDEN_COLUMNS


class LeakageError(ValueError):
    """Raised when a feature table contains a target-outcome column it must not."""


def column_types(X: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Split a feature table into (numeric, categorical) column names.

    Shared by preprocessing/training and explainability so both agree on
    which columns get one-hot encoded vs. scaled.
    """
    categorical = [c for c in X.columns if X[c].dtype == object]
    numeric = [c for c in X.columns if c not in categorical]
    return numeric, categorical


def assert_no_leakage(feature_df: pd.DataFrame, task: str) -> None:
    """Raise LeakageError if any column forbidden for `task` is present.

    This is the project's non-negotiable safeguard (Section G): it must be
    called on every feature table before it reaches training, and it must
    fail loudly -- silently dropping a leaked column would hide the bug
    that put it there in the first place.
    """
    if task not in LEAKAGE_FORBIDDEN_COLUMNS:
        raise ValueError(f"Unknown task '{task}'. Expected one of {sorted(LEAKAGE_FORBIDDEN_COLUMNS)}.")
    forbidden = LEAKAGE_FORBIDDEN_COLUMNS[task]
    present = forbidden.intersection(feature_df.columns)
    if present:
        raise LeakageError(
            f"Forbidden target-outcome column(s) found in features for task '{task}': "
            f"{sorted(present)}. These describe the semester/course being predicted and "
            "must never be used as inputs -- see Section G's leakage guard."
        )


def _session_semester_key(session: pd.Series, semester: pd.Series) -> pd.Series:
    """Chronological sort key for "YYYY/YYYY" session labels + "1"/"2" semesters."""
    year = session.str.slice(0, 4).astype(int)
    return year * 10 + semester.astype(int)


def _zscore(series: pd.Series) -> pd.Series:
    std = series.std(ddof=0)
    if not std or pd.isna(std):
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std


def _course_difficulty_by_semester(enrolments: pd.DataFrame) -> pd.DataFrame:
    """Historical, temporally-safe course difficulty as of each (course, session, semester).

    Difficulty for a given offering is derived only from *strictly prior*
    offerings of the same course (an expanding mean, shifted by one) --
    never from the offering being scored, and never from a later one.
    This is the same kind of population statistic a registrar's published
    historical pass rate would be, not a leak of any individual student's
    outcome for the semester being predicted.
    """
    completed = enrolments[enrolments["status"] == "completed"].dropna(subset=["total_score"])
    per_offering = (
        completed.groupby(["course_id", "session", "semester"])["total_score"].mean().reset_index()
    )
    per_offering["sort_key"] = _session_semester_key(per_offering["session"], per_offering["semester"])
    per_offering = per_offering.sort_values(["course_id", "sort_key"])
    per_offering["prior_mean_score"] = per_offering.groupby("course_id")["total_score"].transform(
        lambda s: s.shift(1).expanding().mean()
    )
    per_offering["difficulty_index"] = 1 - per_offering["prior_mean_score"] / 100
    global_fallback = 1 - completed["total_score"].mean() / 100
    per_offering["difficulty_index"] = per_offering["difficulty_index"].fillna(global_fallback)
    return per_offering[["course_id", "session", "semester", "difficulty_index"]]


def _extended_history(raw_tables: dict[str, pd.DataFrame], include_current: bool) -> pd.DataFrame:
    """academic_history rows, optionally plus one synthetic (unlabeled) row per
    student's current ongoing semester.

    Adding that row *before* the lag computations below means "prior_cgpa",
    "gpa_trend", etc. are derived identically whether the target row is a
    historical semester (training) or the live ongoing one (prediction) --
    each lag simply resolves to "the most recent completed semester's
    values", with no separate code path needed for inference.
    """
    columns = ["student_id", "session", "semester", "credits_registered", "credits_earned", "gpa", "cgpa"]
    history = raw_tables["academic_history"][columns].copy()
    if not include_current:
        return history

    enrolments = raw_tables["enrolments"]
    ongoing = enrolments.loc[enrolments["status"] == "ongoing", ["student_id", "session", "semester"]].drop_duplicates()
    if ongoing.empty:
        return history
    for col in ("credits_registered", "credits_earned", "gpa", "cgpa"):
        ongoing[col] = np.nan
        history[col] = history[col].astype("float64")
    return pd.concat([history, ongoing[columns]], ignore_index=True)


def _build_semester_feature_table(
    raw_tables: dict[str, pd.DataFrame], include_current: bool = False
) -> pd.DataFrame:
    """Core T1/T2 feature computation, shared by training (build_semester_features)
    and live inference (build_prediction_features). Returns one row per target
    (student, session, semester) with every feature column plus gpa/cgpa --
    gpa/cgpa are NaN exactly for the synthetic "current semester" row(s), which
    is how callers tell training rows (labeled) apart from prediction rows.
    """
    students = raw_tables["students"]
    courses = raw_tables["courses"]
    enrolments = raw_tables["enrolments"]
    attendance = raw_tables["attendance"]
    engagement = raw_tables["engagement"]
    history = _extended_history(raw_tables, include_current)

    history["sort_key"] = _session_semester_key(history["session"], history["semester"])
    history = history.sort_values(["student_id", "sort_key"]).reset_index(drop=True)

    # --- academic history (lagged -- strictly prior semesters only) ---
    grouped = history.groupby("student_id")
    history["prior_cgpa"] = grouped["cgpa"].shift(1)
    history["prior_gpa"] = grouped["gpa"].shift(1)
    prior_gpa_window = grouped["gpa"].shift(1)
    history["gpa_trend"] = prior_gpa_window.groupby(history["student_id"]).transform(
        lambda s: s.rolling(3, min_periods=2).apply(lambda w: w.iloc[-1] - w.iloc[0], raw=False)
    )
    history["gpa_volatility"] = prior_gpa_window.groupby(history["student_id"]).transform(
        lambda s: s.rolling(3, min_periods=2).std(ddof=0)
    )
    history["credits_earned_ratio"] = (
        grouped["credits_earned"].transform(lambda s: s.shift(1).expanding().sum())
        / grouped["credits_registered"].transform(lambda s: s.shift(1).expanding().sum())
    )
    history["semesters_completed"] = grouped.cumcount()

    enrolments = enrolments.merge(courses[["id", "level", "credit_units", "is_core"]], left_on="course_id", right_on="id", suffixes=("", "_course"))
    carryover_by_semester = (
        enrolments.groupby(["student_id", "session", "semester"])["is_carryover"].sum().reset_index()
        .rename(columns={"is_carryover": "carryovers_this_semester"})
    )
    carryover_by_semester["sort_key"] = _session_semester_key(
        carryover_by_semester["session"], carryover_by_semester["semester"]
    )
    carryover_by_semester = carryover_by_semester.sort_values(["student_id", "sort_key"])
    carryover_by_semester["carryover_count"] = carryover_by_semester.groupby("student_id")[
        "carryovers_this_semester"
    ].transform(lambda s: s.shift(1).expanding().sum())
    history = history.merge(
        carryover_by_semester[["student_id", "session", "semester", "carryover_count"]],
        on=["student_id", "session", "semester"],
        how="left",
    )

    # --- current-semester performance/attendance (CA + attendance only, never exam/total/grade) ---
    enr_att = enrolments.merge(attendance, left_on="id", right_on="enrolment_id", how="left", suffixes=("", "_att"))
    course_difficulty = _course_difficulty_by_semester(enrolments)
    enr_att = enr_att.merge(course_difficulty, on=["course_id", "session", "semester"], how="left")

    per_semester = enr_att.groupby(["student_id", "session", "semester"]).agg(
        ca_average=("ca_score", "mean"),
        ca_std_dev_across_courses=("ca_score", "std"),
        lowest_ca_score=("ca_score", "min"),
        courses_below_ca_threshold=("ca_score", lambda s: (s < CONTINUOUS_ASSESSMENT_WEIGHT / 2).sum()),
        mean_attendance_rate=("attendance_rate", "mean"),
        min_attendance_rate=("attendance_rate", "min"),
        attendance_std_dev=("attendance_rate", "std"),
        courses_below_75_percent=("attendance_rate", lambda s: (s < 0.75).sum()),
        credit_load=("credit_units", "sum"),
        core_course_ratio=("is_core", "mean"),
        mean_course_difficulty_index=("difficulty_index", "mean"),
        level=("level", lambda s: s.mode().iat[0] if not s.mode().empty else s.iloc[0]),
    ).reset_index()
    per_semester["ca_to_max_ratio"] = per_semester["ca_average"] / CONTINUOUS_ASSESSMENT_WEIGHT

    peer_mean_load = per_semester.groupby(["level", "session", "semester"])["credit_load"].transform("mean")
    per_semester["credit_load_vs_level_mean"] = per_semester["credit_load"] - peer_mean_load

    # --- engagement ---
    eng = engagement.copy()
    eng["submission_rate"] = eng["assignments_submitted"] / eng["assignments_total"]
    eng["punctuality_rate"] = eng["submission_punctuality_rate"]
    eng["lms_logins_normalised"] = _zscore(eng["lms_logins"])
    eng["library_visits_normalised"] = _zscore(eng["library_visits"])
    eng["tutorial_attendance_rate"] = eng["tutorial_attendance"]
    eng = eng[
        [
            "student_id", "session", "semester", "submission_rate", "punctuality_rate",
            "lms_logins_normalised", "study_hours_per_week", "tutorial_attendance_rate",
            "library_visits_normalised",
        ]
    ]

    # --- student-level static attributes (fixed at admission, not time-varying) ---
    static_attrs = students[
        ["id", "entry_mode", "entry_score", "employment_status", "accommodation", "has_scholarship"]
    ].rename(columns={"id": "student_id"})
    static_attrs["entry_score_normalised"] = _zscore(static_attrs["entry_score"])
    static_attrs = static_attrs.drop(columns=["entry_score"])

    features = (
        history[
            [
                "student_id", "session", "semester", "prior_cgpa", "prior_gpa", "gpa_trend",
                "gpa_volatility", "credits_earned_ratio", "carryover_count", "semesters_completed",
                "gpa", "cgpa",
            ]
        ]
        .merge(per_semester, on=["student_id", "session", "semester"], how="left")
        .merge(eng, on=["student_id", "session", "semester"], how="left")
        .merge(static_attrs, on="student_id", how="left")
    )

    # --- interactions ---
    features["attendance_x_ca_average"] = features["mean_attendance_rate"] * features["ca_average"]
    features["study_hours_per_credit_load"] = features["study_hours_per_week"] / features["credit_load"].replace(0, pd.NA)
    features["gpa_trend_x_credit_load"] = features["gpa_trend"] * features["credit_load"]

    return features


def build_semester_features(
    raw_tables: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the shared T1/T2 *training* feature table.

    Returns (features, labels, meta):
    - features: one row per completed (student, session, semester), 25+
      columns, safe to pass straight to assert_no_leakage(..., "risk_classification")
      or assert_no_leakage(..., "gpa_regression").
    - labels: risk_label (T1), target_gpa / target_cgpa (T2) for that same row.
    - meta: student_id, session, semester identifying each row (not a feature).
    """
    full = _build_semester_feature_table(raw_tables, include_current=False)
    labels = pd.DataFrame(
        {
            "risk_label": (full["gpa"] < PROBATION_CGPA_THRESHOLD).astype(int),
            "target_gpa": full["gpa"],
            "target_cgpa": full["cgpa"],
        }
    )
    meta = full[["student_id", "session", "semester"]].copy()
    feature_columns = [c for c in full.columns if c not in {"student_id", "session", "semester", "gpa", "cgpa"}]
    return full[feature_columns], labels, meta


def build_prediction_features(raw_tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build T1/T2 features for every student's current *ongoing* semester.

    This is the live-inference counterpart to build_semester_features: same
    feature columns, same leakage guarantees, but for the semester that
    hasn't finished yet (no gpa/cgpa/risk_label exists to return, since
    that's exactly what's being predicted). A student with no ongoing
    enrolment (fully graduated, or withdrawn) simply has no row here.

    Returns (features, meta) -- meta carries student_id/session/semester.
    """
    full = _build_semester_feature_table(raw_tables, include_current=True)
    current = full[full["gpa"].isna()].reset_index(drop=True)
    meta = current[["student_id", "session", "semester"]].copy()
    feature_columns = [c for c in current.columns if c not in {"student_id", "session", "semester", "gpa", "cgpa"}]
    return current[feature_columns].reset_index(drop=True), meta.reset_index(drop=True)


def build_course_score_features(
    raw_tables: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the T3 feature table: CA and attendance only, per Section G.

    Returns (features, labels, meta) at the (student, course, session,
    semester) grain, restricted to completed enrolments (a known total_score
    is required to train against).
    """
    enrolments = raw_tables["enrolments"]
    attendance = raw_tables["attendance"]

    completed = enrolments[enrolments["status"] == "completed"].dropna(subset=["total_score"])
    joined = completed.merge(attendance, left_on="id", right_on="enrolment_id", how="left", suffixes=("", "_att"))

    features = _course_score_feature_columns(joined)
    labels = pd.DataFrame({"target_total_score": joined["total_score"]})
    meta = joined[["student_id", "course_id", "session", "semester"]].reset_index(drop=True)
    return features, labels.reset_index(drop=True), meta


def _course_score_feature_columns(joined: pd.DataFrame) -> pd.DataFrame:
    features = pd.DataFrame(
        {
            "ca_score": joined["ca_score"],
            "ca_to_max_ratio": joined["ca_score"] / CONTINUOUS_ASSESSMENT_WEIGHT,
            "attendance_rate": joined["attendance_rate"],
            "sessions_attended": joined["sessions_attended"],
            "sessions_held": joined["sessions_held"],
        }
    )
    features["attendance_x_ca_score"] = features["attendance_rate"] * features["ca_score"]
    return features.reset_index(drop=True)


def build_course_prediction_features(raw_tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """T3 features for currently-ongoing enrolments (total_score isn't known yet
    -- that's exactly what's being predicted). Live-inference counterpart to
    build_course_score_features."""
    enrolments = raw_tables["enrolments"]
    attendance = raw_tables["attendance"]

    ongoing = enrolments[enrolments["status"] == "ongoing"]
    joined = ongoing.merge(attendance, left_on="id", right_on="enrolment_id", how="left", suffixes=("", "_att"))

    features = _course_score_feature_columns(joined)
    meta = joined[["student_id", "course_id", "session", "semester"]].reset_index(drop=True)
    return features, meta
