"""CSV import for real institutional student data.

Validates each row against the same rules the Student table and
academic_config enforce, so a real institution's roster loads with zero
code changes -- only a CSV whose headers match REQUIRED_COLUMNS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd
from pydantic import BaseModel, ValidationError, field_validator
from sqlmodel import Session, select

from app.core.academic_config import ENTRY_MODES, LEVELS
from app.db.session import engine
from app.models import Student
from app.models.enums import Accommodation, EmploymentStatus, Gender

REQUIRED_COLUMNS: tuple[str, ...] = (
    "matric_no", "first_name", "last_name", "gender", "date_of_birth",
    "department", "programme", "level", "entry_mode", "entry_score",
    "state_of_origin", "accommodation", "has_scholarship",
    "employment_status", "enrolment_session",
)

_TRUE_STRINGS = {"true", "1", "yes", "y"}


class StudentImportRow(BaseModel):
    """Row-level validation contract for imported student records."""

    matric_no: str
    first_name: str
    last_name: str
    gender: Gender
    date_of_birth: date
    department: str
    programme: str
    level: int
    entry_mode: str
    entry_score: float
    state_of_origin: str
    accommodation: Accommodation
    has_scholarship: bool
    employment_status: EmploymentStatus
    enrolment_session: str

    @field_validator(
        "matric_no", "first_name", "last_name", "department",
        "programme", "state_of_origin", "enrolment_session",
    )
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be blank")
        return value.strip()

    @field_validator("level")
    @classmethod
    def _valid_level(cls, value: int) -> int:
        if value not in LEVELS:
            raise ValueError(f"must be one of {LEVELS}")
        return value

    @field_validator("entry_mode")
    @classmethod
    def _valid_entry_mode(cls, value: str) -> str:
        if value not in ENTRY_MODES:
            raise ValueError(f"must be one of {ENTRY_MODES}")
        return value

    @field_validator("entry_score")
    @classmethod
    def _valid_entry_score(cls, value: float) -> float:
        if not 0 <= value <= 400:
            raise ValueError("must be between 0 and 400")
        return value


@dataclass
class RowError:
    row: int
    field: str
    message: str


@dataclass
class ImportReport:
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: list[RowError]
    inserted: int = 0
    skipped_duplicate_matric_no: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "inserted": self.inserted,
            "skipped_duplicate_matric_no": self.skipped_duplicate_matric_no,
            "errors": [
                {"row": e.row, "field": e.field, "message": e.message} for e in self.errors
            ],
        }


def _coerce_bool(value: object) -> object:
    if isinstance(value, str):
        return value.strip().lower() in _TRUE_STRINGS
    return value


def validate_csv(source) -> tuple[list[StudentImportRow], ImportReport]:
    """Parse and validate a student CSV without touching the database.

    Every value is read as a string first so the Pydantic model -- not
    pandas' type inference -- is the single source of truth for what
    counts as a valid cell.
    """
    df = pd.read_csv(source, dtype=str)
    missing_columns = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_columns:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing_columns)}")

    valid: list[StudentImportRow] = []
    errors: list[RowError] = []
    for idx, raw_row in df.iterrows():
        row_number = int(idx) + 2  # +1 for 0-index, +1 for the header row
        payload = raw_row.where(pd.notnull(raw_row), None).to_dict()
        payload["has_scholarship"] = _coerce_bool(payload.get("has_scholarship"))
        try:
            valid.append(StudentImportRow(**payload))
        except ValidationError as exc:
            for err in exc.errors():
                field_name = ".".join(str(part) for part in err["loc"]) or "row"
                errors.append(RowError(row=row_number, field=field_name, message=err["msg"]))

    return valid, ImportReport(
        total_rows=len(df),
        valid_rows=len(valid),
        invalid_rows=len(df) - len(valid),
        errors=errors,
    )


def import_students_csv(source) -> ImportReport:
    """Validate a student roster CSV and load the valid rows into the database.

    Rows whose matric_no already exists (in the database or earlier in the
    same file) are skipped and listed in the report rather than raising --
    a partial, well-reported import is more useful for a real institution's
    messy export than an all-or-nothing failure.
    """
    valid_rows, report = validate_csv(source)

    with Session(engine) as session:
        existing_matric_nos = set(session.exec(select(Student.matric_no)).all())
        seen_in_file: set[str] = set()
        to_insert: list[Student] = []
        for row in valid_rows:
            if row.matric_no in existing_matric_nos or row.matric_no in seen_in_file:
                report.skipped_duplicate_matric_no.append(row.matric_no)
                continue
            seen_in_file.add(row.matric_no)
            to_insert.append(Student(**row.model_dump()))
        session.add_all(to_insert)
        session.commit()
        report.inserted = len(to_insert)

    return report
