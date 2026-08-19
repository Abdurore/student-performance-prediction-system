"""Synthetic institutional dataset generator.

Produces a causally coherent dataset -- not random noise -- for
``N_STUDENTS`` students studied across ``N_SESSIONS`` academic sessions.
Every student carries one persistent latent "ability" trait that drives
attendance, continuous assessment, examination performance, and engagement
together, which is what makes the documented correlations (attendance with
CA/final score, prior CGPA with next-semester GPA, employment status with
study hours/attendance) emerge naturally rather than needing to be
hand-forced after the fact. A dataset generated purely from independent
random columns would let Phase 3 models "succeed" without having learned a
real signal, which would undermine the methodological-defensibility goal
of this project.

Random state is seeded and recorded (see ``generation_metadata.json``) so
the dataset -- and therefore every reported model metric -- is reproducible.

Run standalone to regenerate the CSVs under ``data/raw/`` and print a
calibration report (grade distribution, key correlations):

    python -m ml.data_generator
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from app.core.academic_config import grade_for_score
from ml.config import MISSINGNESS_RATE_RANGE, N_SESSIONS, N_STUDENTS, RANDOM_SEED

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW_DIR = REPO_ROOT / "data" / "raw"

# Nigerian tertiary degree-classification bands on the 5.00 GPA_SCALE,
# used only to steer the generator's ability distribution toward the
# target classification mix -- not persisted anywhere.
_CLASSIFICATION_BOUNDS = (
    ("first_class", 4.50, 5.01),
    ("second_upper", 3.50, 4.50),
    ("second_lower", 2.40, 3.50),
    ("third_class", 1.50, 2.40),
    ("pass_fail", 0.00, 1.50),
)
_TARGET_CLASSIFICATION_SHARE = {
    "first_class": 0.08,
    "second_upper": 0.30,
    "second_lower": 0.38,
    "third_class": 0.18,
    "pass_fail": 0.06,
}

_SESSION_START_YEAR = 2019


@dataclass(frozen=True)
class Department:
    name: str
    code: str
    programme_length_years: int


DEPARTMENTS: tuple[Department, ...] = (
    Department("Computer Science", "CSC", 4),
    Department("Economics", "ECO", 4),
    Department("Accounting", "ACC", 4),
    Department("Mass Communication", "MCM", 4),
    Department("Civil Engineering", "CVE", 5),
    Department("Electrical Engineering", "EEE", 5),
)

STATES_OF_ORIGIN = (
    "Lagos", "Kano", "Rivers", "Oyo", "Kaduna", "Enugu", "Delta", "Anambra",
    "Edo", "Plateau", "Cross River", "Ogun", "Imo", "Borno", "Sokoto",
)

COURSE_TITLE_TOPICS = (
    "Foundations", "Principles", "Analysis", "Systems", "Methods",
    "Theory", "Practice", "Applications", "Design", "Seminar",
)


def academic_sessions() -> list[str]:
    """Return the N_SESSIONS session labels the generator spans, oldest first."""
    return [
        f"{_SESSION_START_YEAR + i}/{_SESSION_START_YEAR + i + 1}"
        for i in range(N_SESSIONS)
    ]


def build_course_catalog(rng: np.random.Generator) -> tuple[pd.DataFrame, dict[int, float]]:
    """Build the course catalogue with a hidden per-course difficulty index.

    Difficulty is assigned before any score is generated (not derived from
    outcomes afterwards) so that "harder courses have lower pass rates" is
    a genuine causal input, mirroring how course difficulty works in
    reality and letting the Phase 8 course-difficulty analytics endpoint
    later rediscover it from observed failure rates.
    """
    rows: list[dict] = []
    difficulty_by_code_index: dict[int, float] = {}
    course_id = 1
    for dept in DEPARTMENTS:
        max_level = 100 + 100 * (dept.programme_length_years - 1)
        levels = range(100, max_level + 1, 100)
        for level in levels:
            for semester in ("1", "2"):
                n_courses = rng.integers(4, 7)
                for idx in range(n_courses):
                    difficulty = float(np.clip(rng.normal(0, 1), -2.2, 2.2))
                    credit_units = int(rng.choice([2, 3, 3, 4]))
                    is_core = bool(rng.random() < 0.75)
                    topic = rng.choice(COURSE_TITLE_TOPICS)
                    rows.append(
                        {
                            "id": course_id,
                            "course_code": f"{dept.code}{level}{semester}{idx + 1}",
                            "title": f"{dept.name} {topic} {level // 100}0{idx + 1}",
                            "credit_units": credit_units,
                            "level": level,
                            "semester": semester,
                            "department": dept.name,
                            "lecturer_id": None,  # assigned in build_users
                            "is_core": is_core,
                        }
                    )
                    difficulty_by_code_index[course_id] = difficulty
                    course_id += 1
    return pd.DataFrame(rows), difficulty_by_code_index


def build_students(rng: np.random.Generator, sessions: list[str]) -> tuple[pd.DataFrame, np.ndarray]:
    """Build the student roster plus each student's latent ability trait.

    Ability is the single hidden driver shared by attendance, CA, exam,
    and engagement generation -- it is what makes those signals correlate
    with each other and with GPA the way real academic performance does.
    """
    dept_weights = np.array([1.0 if d.programme_length_years == 4 else 0.6 for d in DEPARTMENTS])
    dept_weights = dept_weights / dept_weights.sum()
    dept_choice = rng.choice(len(DEPARTMENTS), size=N_STUDENTS, p=dept_weights)

    entry_session_idx = rng.integers(0, N_SESSIONS, size=N_STUDENTS)
    entry_modes = rng.choice(
        ["UTME", "Direct Entry", "Transfer"], size=N_STUDENTS, p=[0.78, 0.17, 0.05]
    )
    genders = rng.choice(["male", "female"], size=N_STUDENTS, p=[0.54, 0.46])
    accommodations = rng.choice(["on_campus", "off_campus"], size=N_STUDENTS, p=[0.4, 0.6])
    has_scholarship = rng.random(N_STUDENTS) < 0.08
    employment_status = rng.choice(
        ["none", "part_time", "full_time"], size=N_STUDENTS, p=[0.72, 0.20, 0.08]
    )
    # Wider than a standard normal so between-student final-CGPA spread is
    # large enough to populate the tails of the target degree-classification
    # mix (first class and pass/fail) rather than bunching in the middle.
    ability = rng.normal(0, 1.2, size=N_STUDENTS)

    rows: list[dict] = []
    for i in range(N_STUDENTS):
        dept = DEPARTMENTS[dept_choice[i]]
        entry_idx = int(entry_session_idx[i])
        entry_year = _SESSION_START_YEAR + entry_idx
        entry_mode = entry_modes[i]
        base_score = 180 + ability[i] * 25
        entry_score = float(np.clip(base_score + rng.normal(0, 15), 120, 300))
        dob_year = entry_year - int(rng.integers(17, 23))
        dob = date(dob_year, int(rng.integers(1, 13)), int(rng.integers(1, 28)))
        rows.append(
            {
                "id": i + 1,
                "matric_no": f"{dept.code}/{entry_year % 100:02d}/{i + 1:05d}",
                "first_name": f"Student{i + 1:04d}",
                "last_name": f"{dept.code}Family{i + 1:04d}",
                "gender": genders[i],
                "date_of_birth": dob,
                "department": dept.name,
                "programme": f"B.Sc. {dept.name}" if dept.programme_length_years == 4 else f"B.Eng. {dept.name}",
                "level": 100,  # finalized after trajectory simulation
                "entry_mode": entry_mode,
                "entry_score": round(entry_score, 2),
                "state_of_origin": rng.choice(STATES_OF_ORIGIN),
                "accommodation": accommodations[i],
                "has_scholarship": bool(has_scholarship[i]),
                "employment_status": employment_status[i],
                "adviser_id": None,  # assigned in build_users
                "enrolment_session": sessions[entry_idx],
                "is_active": True,  # finalized after trajectory simulation
                "_dept_code": dept.code,
                "_programme_years": dept.programme_length_years,
                "_entry_session_idx": entry_idx,
            }
        )
    return pd.DataFrame(rows), ability


def build_users(rng: np.random.Generator, students_df: pd.DataFrame, courses_df: pd.DataFrame) -> pd.DataFrame:
    """Build login accounts: one admin, lecturers, advisers, and one per student.

    A shared, documented demo password is used for every seeded account
    (see docs/user-manual.md once written) -- acceptable for an offline
    academic demo and required by Section I's "visible demo credentials".
    """
    from app.core.security import hash_password

    demo_hash = hash_password("Demo@12345")
    rows: list[dict] = []
    user_id = 1

    rows.append(
        {"id": user_id, "email": "admin@university.edu.ng", "password_hash": demo_hash,
         "full_name": "System Administrator", "role": "admin", "student_id": None, "is_active": True}
    )
    user_id += 1

    n_lecturers = 18
    lecturer_ids: list[int] = []
    for i in range(n_lecturers):
        rows.append(
            {"id": user_id, "email": f"lecturer{i + 1:02d}@university.edu.ng", "password_hash": demo_hash,
             "full_name": f"Dr. Lecturer {i + 1:02d}", "role": "lecturer", "student_id": None, "is_active": True}
        )
        lecturer_ids.append(user_id)
        user_id += 1

    n_advisers = 24
    adviser_ids: list[int] = []
    for i in range(n_advisers):
        rows.append(
            {"id": user_id, "email": f"adviser{i + 1:02d}@university.edu.ng", "password_hash": demo_hash,
             "full_name": f"Adviser {i + 1:02d}", "role": "adviser", "student_id": None, "is_active": True}
        )
        adviser_ids.append(user_id)
        user_id += 1

    for _, student in students_df.iterrows():
        rows.append(
            {
                "id": user_id,
                "email": f"{student['matric_no'].lower().replace('/', '.')}@university.edu.ng",
                "password_hash": demo_hash,
                "full_name": f"{student['first_name']} {student['last_name']}",
                "role": "student",
                "student_id": int(student["id"]),
                "is_active": True,
            }
        )
        user_id += 1

    courses_df["lecturer_id"] = rng.choice(lecturer_ids, size=len(courses_df))
    students_df["adviser_id"] = rng.choice(adviser_ids, size=len(students_df))

    return pd.DataFrame(rows)


def simulate_academic_records(
    rng: np.random.Generator,
    students_df: pd.DataFrame,
    courses_df: pd.DataFrame,
    difficulty_by_course: dict[int, float],
    ability: np.ndarray,
    sessions: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Simulate each student's semester-by-semester trajectory.

    Each semester's attendance, CA, exam, and engagement figures are drawn
    from the student's persistent ability trait plus an employment penalty
    plus course difficulty plus noise -- the shared ability term is what
    produces the target attendance/CA/exam correlations and the prior-CGPA
    -> next-GPA correlation, since ability (and therefore performance)
    persists across semesters while noise does not.

    The most recent semester of any student who has not yet finished their
    programme is left "ongoing" (no exam/total/grade, no academic_history
    row yet) -- this is deliberate: it gives the later prediction phases a
    real population of "currently enrolled, outcome not yet known"
    students to predict for, which is the whole point of early prediction.
    """
    courses_by_key: dict[tuple[str, int, str], pd.DataFrame] = {
        key: group for key, group in courses_df.groupby(["department", "level", "semester"])
    }

    enrolment_rows: list[dict] = []
    attendance_rows: list[dict] = []
    engagement_rows: list[dict] = []
    history_rows: list[dict] = []

    enrolment_id = 1
    attendance_id = 1
    engagement_id = 1
    history_id = 1

    employment_attendance_penalty = {"none": 0.0, "part_time": -0.06, "full_time": -0.14}
    employment_hours_penalty = {"none": 0.0, "part_time": 4.0, "full_time": 10.0}

    for row_idx, student in students_df.iterrows():
        student_id = int(student["id"])
        dept = student["department"]
        entry_idx = int(student["_entry_session_idx"])
        programme_years = int(student["_programme_years"])
        max_level = 100 + 100 * (programme_years - 1)
        max_semesters = programme_years * 2
        available_semesters = (N_SESSIONS - entry_idx) * 2
        n_semesters = int(min(max_semesters, available_semesters))
        student_ability = float(ability[row_idx])
        emp_status = student["employment_status"]

        cumulative_points = 0.0
        cumulative_units = 0
        final_level_reached = 100
        completed_all = n_semesters >= max_semesters

        for t in range(n_semesters):
            session = sessions[entry_idx + t // 2]
            semester = "1" if t % 2 == 0 else "2"
            level = 100 + 100 * (t // 2)
            final_level_reached = level
            is_last_semester = t == n_semesters - 1
            is_ongoing = is_last_semester and not completed_all

            key = (dept, level, semester)
            available_courses = courses_by_key.get(key)
            if available_courses is None or available_courses.empty:
                continue
            n_take = min(len(available_courses), int(rng.integers(5, 8)))
            taken = available_courses.sample(n=n_take, random_state=rng.integers(0, 2**32 - 1))

            mean_attendance_this_semester: list[float] = []
            semester_points = 0.0
            semester_units = 0

            # A per-semester shock (on top of the persistent ability trait)
            # represents that semester's circumstances (health, personal
            # events, a hard course load). Without it, cumulative CGPA would
            # converge almost deterministically onto ability and the
            # prior-CGPA/next-GPA correlation would run far above the
            # documented ~0.65 target -- this is what keeps it realistic.
            semester_shock = float(rng.normal(0, 0.55))
            performance = 0.65 * student_ability + semester_shock

            for _, course in taken.iterrows():
                course_id = int(course["id"])
                difficulty = difficulty_by_course[course_id]
                emp_penalty = employment_attendance_penalty[emp_status]

                attendance_rate = float(
                    np.clip(
                        0.83 + 0.04 * student_ability + emp_penalty - 0.01 * difficulty + rng.normal(0, 0.11),
                        0.2,
                        1.0,
                    )
                )
                mean_attendance_this_semester.append(attendance_rate)
                sessions_held = int(rng.integers(12, 16))
                sessions_attended = int(round(attendance_rate * sessions_held))

                ca_score = float(
                    np.clip(
                        10 + 13 * attendance_rate + 2.4 * performance - 1.3 * difficulty + rng.normal(0, 2.0),
                        0,
                        30,
                    )
                )
                exam_score = None
                total_score = None
                grade = None
                grade_point = None

                if not is_ongoing:
                    exam_score = float(
                        np.clip(
                            26.3 + 14 * attendance_rate + 6.5 * performance - 3.5 * difficulty + rng.normal(0, 4.5),
                            0,
                            70,
                        )
                    )
                    total_score = float(np.clip(ca_score + exam_score, 0, 100))
                    grade, grade_point = grade_for_score(round(total_score, 2))
                    semester_points += grade_point * int(course["credit_units"])
                    semester_units += int(course["credit_units"])

                enrolment_rows.append(
                    {
                        "id": enrolment_id,
                        "student_id": student_id,
                        "course_id": course_id,
                        "session": session,
                        "semester": semester,
                        "ca_score": round(ca_score, 2),
                        "exam_score": round(exam_score, 2) if exam_score is not None else None,
                        "total_score": round(total_score, 2) if total_score is not None else None,
                        "grade": grade,
                        "grade_point": grade_point,
                        "status": "ongoing" if is_ongoing else "completed",
                        "is_carryover": bool(grade == "F") if grade else False,
                    }
                )
                attendance_rows.append(
                    {
                        "id": attendance_id,
                        "enrolment_id": enrolment_id,
                        "sessions_held": sessions_held,
                        "sessions_attended": sessions_attended,
                        "attendance_rate": round(attendance_rate, 4),
                        "last_updated": datetime.now(timezone.utc),
                    }
                )
                enrolment_id += 1
                attendance_id += 1

            mean_att = float(np.mean(mean_attendance_this_semester)) if mean_attendance_this_semester else 0.8
            hours_penalty = employment_hours_penalty[emp_status]
            study_hours = float(np.clip(17 + 6 * student_ability - hours_penalty + rng.normal(0, 3), 1, 45))
            assignments_total = int(rng.integers(6, 11))
            submission_fraction = float(np.clip(0.55 + 0.35 * mean_att + rng.normal(0, 0.08), 0, 1))
            assignments_submitted = int(round(assignments_total * submission_fraction))
            punctuality = float(np.clip(0.5 + 0.4 * mean_att + rng.normal(0, 0.1), 0, 1))
            lms_logins = int(max(0, round(20 + 25 * mean_att + 8 * student_ability + rng.normal(0, 6))))
            library_visits = int(max(0, round(6 + 8 * mean_att - 0.4 * hours_penalty + rng.normal(0, 3))))
            tutorial_attendance = float(np.clip(mean_att + rng.normal(0, 0.07), 0, 1))
            extracurricular_hours = float(np.clip(3 + rng.normal(0, 2) - 0.05 * hours_penalty, 0, 12))

            engagement_rows.append(
                {
                    "id": engagement_id,
                    "student_id": student_id,
                    "session": session,
                    "semester": semester,
                    "assignments_submitted": assignments_submitted,
                    "assignments_total": assignments_total,
                    "submission_punctuality_rate": round(punctuality, 4),
                    "lms_logins": lms_logins,
                    "library_visits": library_visits,
                    "study_hours_per_week": round(study_hours, 2),
                    "tutorial_attendance": round(tutorial_attendance, 4),
                    "extracurricular_hours": round(extracurricular_hours, 2),
                }
            )
            engagement_id += 1

            if not is_ongoing and semester_units > 0:
                gpa = semester_points / semester_units
                cumulative_points += semester_points
                cumulative_units += semester_units
                cgpa = cumulative_points / cumulative_units
                if cgpa < 2.0:
                    standing = "probation"
                elif cgpa < 2.5:
                    standing = "warning"
                else:
                    standing = "good"
                history_rows.append(
                    {
                        "id": history_id,
                        "student_id": student_id,
                        "session": session,
                        "semester": semester,
                        "credits_registered": semester_units,
                        "credits_earned": semester_units,  # overwritten below from actual pass/fail outcomes
                        "gpa": round(gpa, 3),
                        "cgpa": round(cgpa, 3),
                        "standing": standing,
                    }
                )
                history_id += 1

        students_df.at[row_idx, "level"] = min(final_level_reached, max_level)
        students_df.at[row_idx, "is_active"] = not completed_all

    enrolments_df = pd.DataFrame(enrolment_rows)
    attendance_df = pd.DataFrame(attendance_rows)
    engagement_df = pd.DataFrame(engagement_rows)
    history_df = pd.DataFrame(history_rows)

    # credits_earned = credit units of courses actually passed (grade != F) that semester
    passed_units = (
        enrolments_df[enrolments_df["status"] == "completed"]
        .merge(courses_df[["id", "credit_units"]], left_on="course_id", right_on="id", suffixes=("", "_course"))
        .assign(earned=lambda d: np.where(d["grade"] != "F", d["credit_units"], 0))
        .groupby(["student_id", "session", "semester"])["earned"]
        .sum()
        .reset_index()
    )
    history_df = history_df.merge(passed_units, on=["student_id", "session", "semester"], how="left")
    history_df["credits_earned"] = history_df["earned"].fillna(history_df["credits_registered"]).astype(int)
    history_df = history_df.drop(columns=["earned"])

    return enrolments_df, attendance_df, engagement_df, history_df


def inject_missingness(rng: np.random.Generator, attendance_df: pd.DataFrame, engagement_df: pd.DataFrame) -> None:
    """Null out 4-8% of values in attendance/engagement columns, independently per column.

    Mutates the frames in place. Structural nulls (ongoing-semester exam
    scores) are produced separately in simulate_academic_records and are
    NOT part of this randomised missingness -- they represent "not yet
    known", not "data entry gap", and mixing the two would make the
    cleaning exercise unrealistic.
    """
    low, high = MISSINGNESS_RATE_RANGE
    attendance_cols = ["sessions_held", "sessions_attended", "attendance_rate"]
    engagement_cols = [
        "assignments_submitted", "assignments_total", "submission_punctuality_rate",
        "lms_logins", "library_visits", "study_hours_per_week",
        "tutorial_attendance", "extracurricular_hours",
    ]
    for col in attendance_cols:
        rate = rng.uniform(low, high)
        mask = rng.random(len(attendance_df)) < rate
        attendance_df.loc[mask, col] = np.nan
    for col in engagement_cols:
        rate = rng.uniform(low, high)
        mask = rng.random(len(engagement_df)) < rate
        engagement_df.loc[mask, col] = np.nan


def generate_dataset(seed: int = RANDOM_SEED) -> dict[str, pd.DataFrame]:
    """Generate the full synthetic dataset and return it as named DataFrames."""
    rng = np.random.default_rng(seed)
    sessions = academic_sessions()

    courses_df, difficulty_by_course = build_course_catalog(rng)
    students_df, ability = build_students(rng, sessions)
    users_df = build_users(rng, students_df, courses_df)
    enrolments_df, attendance_df, engagement_df, history_df = simulate_academic_records(
        rng, students_df, courses_df, difficulty_by_course, ability, sessions
    )
    inject_missingness(rng, attendance_df, engagement_df)

    students_df = students_df.drop(columns=["_dept_code", "_programme_years", "_entry_session_idx"])

    return {
        "users": users_df,
        "students": students_df,
        "courses": courses_df,
        "enrolments": enrolments_df,
        "attendance": attendance_df,
        "engagement": engagement_df,
        "academic_history": history_df,
    }


def classify_cgpa(cgpa: float) -> str:
    for name, low, high in _CLASSIFICATION_BOUNDS:
        if low <= cgpa < high:
            return name
    return "pass_fail"


def calibration_report(dataset: dict[str, pd.DataFrame]) -> dict:
    """Compute the statistics used to sanity-check the generator's calibration."""
    enrolments = dataset["enrolments"]
    attendance = dataset["attendance"]
    history = dataset["academic_history"]

    joined = enrolments.merge(
        attendance[["enrolment_id", "attendance_rate"]],
        left_on="id",
        right_on="enrolment_id",
        how="inner",
    ).dropna(subset=["attendance_rate", "ca_score"])
    completed = joined.dropna(subset=["total_score"])

    corr_attendance_ca = float(joined["attendance_rate"].corr(joined["ca_score"]))
    corr_attendance_total = float(completed["attendance_rate"].corr(completed["total_score"]))

    latest_cgpa_by_student = (
        history.sort_values(["student_id", "session", "semester"])
        .groupby("student_id")
        .tail(1)
        .set_index("student_id")["cgpa"]
    )
    history_sorted = history.sort_values(["student_id", "session", "semester"]).reset_index(drop=True)
    history_sorted["prior_cgpa"] = history_sorted.groupby("student_id")["cgpa"].shift(1)
    prior_next = history_sorted.dropna(subset=["prior_cgpa"])
    corr_prior_cgpa_next_gpa = float(prior_next["prior_cgpa"].corr(prior_next["gpa"]))

    classification_counts = latest_cgpa_by_student.apply(classify_cgpa).value_counts(normalize=True).to_dict()

    return {
        "n_students": int(dataset["students"].shape[0]),
        "n_enrolments": int(enrolments.shape[0]),
        "correlation_attendance_vs_ca_score": round(corr_attendance_ca, 3),
        "correlation_attendance_vs_total_score": round(corr_attendance_total, 3),
        "correlation_prior_cgpa_vs_next_gpa": round(corr_prior_cgpa_next_gpa, 3),
        "classification_distribution": {k: round(v, 3) for k, v in classification_counts.items()},
        "target_classification_distribution": _TARGET_CLASSIFICATION_SHARE,
    }


def save_dataset(dataset: dict[str, pd.DataFrame], out_dir: Path = DATA_RAW_DIR) -> None:
    """Persist every table as CSV under data/raw/ for inspection and CSV-import testing."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in dataset.items():
        df.to_csv(out_dir / f"{name}.csv", index=False)
    metadata = {
        "seed": RANDOM_SEED,
        "n_students": N_STUDENTS,
        "n_sessions": N_SESSIONS,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (out_dir / "generation_metadata.json").write_text(json.dumps(metadata, indent=2))


def main() -> None:
    dataset = generate_dataset()
    save_dataset(dataset)
    report = calibration_report(dataset)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
