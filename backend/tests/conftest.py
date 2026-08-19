"""Shared fixtures: a small synthetic dataset loaded into an isolated temp DB.

Used by test_features.py and test_train.py so neither depends on `make
seed` having been run against the shared demo database.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.db import seed as seed_module
from app.models import AcademicHistory, Attendance, Course, Engagement, Enrolment, Student, User
from ml import preprocessing
from ml.data_generator import generate_dataset

_LOAD_ORDER = (
    (User, "users"),
    (Student, "students"),
    (Course, "courses"),
    (Enrolment, "enrolments"),
    (Attendance, "attendance"),
    (Engagement, "engagement"),
    (AcademicHistory, "academic_history"),
)


@pytest.fixture(scope="module")
def small_db_engine(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    mp.setattr("ml.data_generator.N_STUDENTS", 80)
    dataset = generate_dataset(seed=7)
    mp.undo()

    db_path = tmp_path_factory.mktemp("small_db") / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        for model, table_name in _LOAD_ORDER:
            seed_module._bulk_insert(session, model, seed_module._records(dataset[table_name], table_name))
            session.commit()
    return engine


@pytest.fixture(scope="module")
def raw_tables(small_db_engine):
    mp = pytest.MonkeyPatch()
    mp.setattr(preprocessing, "engine", small_db_engine)
    tables = preprocessing.load_raw_tables()
    mp.undo()
    return tables
