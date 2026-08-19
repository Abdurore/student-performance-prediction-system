"""Load the synthetic dataset (or any dataset shaped like it) into the database.

Schema creation is Alembic's job (`alembic upgrade head`), not this
module's -- seeding only ever inserts rows into an already-migrated schema
so there is one source of truth for the schema shape.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, insert
from sqlmodel import Session

from app.db.session import engine
from app.models import (
    AcademicHistory,
    Attendance,
    Course,
    Engagement,
    Enrolment,
    Student,
    User,
)
from ml.data_generator import calibration_report, generate_dataset, save_dataset

# Columns that must stay integers even though missingness injection or an
# "unset" sentinel gives their pandas column a float dtype (NaN forces
# float64 on an otherwise-integer column).
_INT_FIELDS: dict[str, frozenset[str]] = {
    "enrolments": frozenset({"grade_point"}),
    "attendance": frozenset({"sessions_held", "sessions_attended"}),
    "engagement": frozenset(
        {"assignments_submitted", "assignments_total", "lms_logins", "library_visits"}
    ),
}


def _records(df: pd.DataFrame, table_name: str) -> list[dict]:
    """Convert a generator DataFrame to DB-ready records (NaN -> None, ints restored)."""
    int_fields = _INT_FIELDS.get(table_name, frozenset())
    records: list[dict] = []
    for row in df.to_dict(orient="records"):
        clean: dict = {}
        for key, value in row.items():
            if isinstance(value, float) and math.isnan(value):
                clean[key] = None
            elif key in int_fields and value is not None:
                clean[key] = int(value)
            else:
                clean[key] = value
        records.append(clean)
    return records


def _bulk_insert(session: Session, model: type, records: list[dict]) -> None:
    if not records:
        return
    session.execute(insert(model), records)


def reset_schema() -> None:
    """Delete all rows from every seeded table, in FK-safe order.

    Used instead of dropping the SQLite file so `make seed` stays a single
    idempotent step that leaves the Alembic-managed schema untouched.
    """
    with Session(engine) as session:
        for model in (
            AcademicHistory,
            Engagement,
            Attendance,
            Enrolment,
            Course,
            Student,
            User,
        ):
            session.execute(delete(model))
        session.commit()


def load_dataset(dataset: dict[str, pd.DataFrame]) -> None:
    """Bulk-insert a generator-shaped dataset, preserving its explicit ids."""
    with Session(engine) as session:
        _bulk_insert(session, User, _records(dataset["users"], "users"))
        session.commit()
        _bulk_insert(session, Student, _records(dataset["students"], "students"))
        session.commit()
        _bulk_insert(session, Course, _records(dataset["courses"], "courses"))
        session.commit()
        _bulk_insert(session, Enrolment, _records(dataset["enrolments"], "enrolments"))
        session.commit()
        _bulk_insert(session, Attendance, _records(dataset["attendance"], "attendance"))
        session.commit()
        _bulk_insert(session, Engagement, _records(dataset["engagement"], "engagement"))
        session.commit()
        _bulk_insert(
            session, AcademicHistory, _records(dataset["academic_history"], "academic_history")
        )
        session.commit()


def run_seed(save_csv: bool = True, csv_dir: Path | None = None) -> dict:
    """Regenerate the synthetic dataset and load it into the database.

    Returns the calibration report (correlation matrix + grade
    distribution) so callers -- `make seed` and its tests -- can verify
    the Phase 1 gate without re-reading the database.
    """
    dataset = generate_dataset()
    if save_csv:
        if csv_dir:
            save_dataset(dataset, out_dir=csv_dir)
        else:
            save_dataset(dataset)
    reset_schema()
    load_dataset(dataset)
    return calibration_report(dataset)


if __name__ == "__main__":
    import json

    print(json.dumps(run_seed(), indent=2))
