"""Tests for the real-institutional-data CSV import path."""

import io

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.db import csv_import
from app.models import Student

VALID_CSV = """matric_no,first_name,last_name,gender,date_of_birth,department,programme,level,entry_mode,entry_score,state_of_origin,accommodation,has_scholarship,employment_status,enrolment_session
CSC/24/00001,Amaka,Obi,female,2003-05-14,Computer Science,B.Sc. Computer Science,100,UTME,245,Lagos,on_campus,false,none,2024/2025
ECO/24/00002,Tunde,Balogun,male,2002-11-02,Economics,B.Sc. Economics,100,Direct Entry,210,Oyo,off_campus,true,part_time,2024/2025
"""


@pytest.fixture()
def temp_engine(monkeypatch, tmp_path):
    """Point csv_import at an isolated in-memory-backed schema, not the demo DB."""
    engine = create_engine(f"sqlite:///{tmp_path}/test_import.db")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(csv_import, "engine", engine)
    return engine


def test_import_valid_rows(temp_engine) -> None:
    report = csv_import.import_students_csv(io.StringIO(VALID_CSV))
    assert report.total_rows == 2
    assert report.valid_rows == 2
    assert report.inserted == 2
    assert report.errors == []

    with Session(temp_engine) as session:
        matric_nos = session.exec(select(Student.matric_no)).all()
    assert set(matric_nos) == {"CSC/24/00001", "ECO/24/00002"}


def test_duplicate_matric_no_is_skipped_not_erroring(temp_engine) -> None:
    csv_import.import_students_csv(io.StringIO(VALID_CSV))
    report = csv_import.import_students_csv(io.StringIO(VALID_CSV))
    assert report.inserted == 0
    assert sorted(report.skipped_duplicate_matric_no) == ["CSC/24/00001", "ECO/24/00002"]


def test_invalid_rows_are_reported_with_row_and_field(temp_engine) -> None:
    bad_row = (
        "CSC/24/00003,,Obi,female,2003-05-14,Computer Science,"
        "B.Sc. Computer Science,999,UTME,245,Lagos,on_campus,false,none,2024/2025\n"
    )
    report = csv_import.import_students_csv(io.StringIO(VALID_CSV + bad_row))
    assert report.total_rows == 3
    assert report.invalid_rows == 1
    assert report.inserted == 2  # the two good rows still load
    fields_with_errors = {e.field for e in report.errors}
    assert "first_name" in fields_with_errors
    assert "level" in fields_with_errors
    assert all(e.row == 4 for e in report.errors)  # header + 2 good rows + this row


def test_missing_required_column_raises_before_any_row_is_checked() -> None:
    incomplete_csv = "matric_no,first_name\nCSC/24/00001,Amaka\n"
    with pytest.raises(ValueError, match="missing required columns"):
        csv_import.validate_csv(io.StringIO(incomplete_csv))
