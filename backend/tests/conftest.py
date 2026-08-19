"""Shared fixtures: a small synthetic dataset loaded into an isolated temp DB.

Used by test_features.py, test_train.py, test_explain.py, test_fairness.py,
test_api_roles.py, and the service-layer tests so none of them depend on
`make seed` having been run against the shared demo database.
"""

from datetime import date, datetime, timezone

import joblib
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline
from sqlmodel import Session, SQLModel, create_engine

from app.core.security import hash_password
from app.db import seed as seed_module
from app.db import session as db_session_module
from app.main import app
from app.models import AcademicHistory, Attendance, Course, Engagement, Enrolment, ModelRegistry, Student, User
from app.models.enums import Accommodation, Gender, UserRole
from ml import explain as explain_module
from ml import fairness as fairness_module
from ml import preprocessing
from ml import preprocessing as preprocessing_module
from ml import train as train_module
from ml.data_generator import generate_dataset
from ml.features import build_semester_features, column_types
from ml.preprocessing import build_preprocessing_pipeline

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


@pytest.fixture(scope="module")
def trained_registry(tmp_path_factory, raw_tables, small_db_engine):
    """Fit + register one plain (untuned) model each for T1, T2, and T3
    directly, bypassing ml.train's GridSearchCV/SMOTE machinery -- explain.py,
    fairness.py, and the prediction service only need *an* active model per
    task, and fitting one pipeline directly is far faster than a full
    train_task() run."""
    from ml.features import build_course_score_features

    X, y_df, _meta = build_semester_features(raw_tables)
    numeric_cols, categorical_cols = column_types(X)
    X_course, y_course_df, _meta_course = build_course_score_features(raw_tables)
    course_numeric_cols, course_categorical_cols = column_types(X_course)
    artifacts_dir = tmp_path_factory.mktemp("explain_fairness_artifacts")

    specs = (
        ("risk_classification", "logistic_regression", LogisticRegression(max_iter=1000), X, numeric_cols, categorical_cols, y_df["risk_label"]),
        ("gpa_regression", "linear_regression", LinearRegression(), X, numeric_cols, categorical_cols, y_df["target_gpa"]),
        ("course_score", "linear_regression", LinearRegression(), X_course, course_numeric_cols, course_categorical_cols, y_course_df["target_total_score"]),
    )
    with Session(small_db_engine) as session:
        for task, algo, estimator, X, numeric_cols, categorical_cols, y in specs:
            pipeline = Pipeline(
                steps=[("preprocess", build_preprocessing_pipeline(numeric_cols, categorical_cols)), ("model", estimator)]
            )
            pipeline.fit(X, y)
            model_path = artifacts_dir / f"{task}__{algo}.joblib"
            joblib.dump(pipeline, model_path)
            session.add(
                ModelRegistry(
                    version=f"{task}__{algo}",
                    task=task,
                    algorithm=algo,
                    trained_at=datetime.now(timezone.utc),
                    training_rows=len(X),
                    feature_list=list(X.columns),
                    hyperparameters={},
                    metrics={},
                    artifact_path=str(model_path),
                    is_active=True,
                )
            )
        session.commit()
    return artifacts_dir


@pytest.fixture()
def api_client(trained_registry, small_db_engine):
    """A FastAPI TestClient wired to the isolated small test DB.

    Every module that binds its own `engine` name gets monkeypatched to
    match -- app.db.session backs the get_session dependency every router
    uses; ml.explain/ml.fairness/ml.preprocessing/ml.train are imported
    directly by the prediction/analytics/model services. Depending on this
    fixture (even without using the returned client) is the standard way
    for a test to call service functions directly against the same DB.
    """
    mp = pytest.MonkeyPatch()
    for module in (db_session_module, preprocessing_module, explain_module, fairness_module, train_module):
        mp.setattr(module, "engine", small_db_engine)
    yield TestClient(app)
    mp.undo()


@pytest.fixture(scope="module")
def demo_users(small_db_engine):
    """One user per role, plus a second student to test cross-student access."""
    with Session(small_db_engine) as session:
        pwd = hash_password("Password123!")
        admin = User(email="role-admin@university.edu.ng", password_hash=pwd, full_name="Role Admin", role=UserRole.ADMIN)
        lecturer = User(email="role-lecturer@university.edu.ng", password_hash=pwd, full_name="Role Lecturer", role=UserRole.LECTURER)
        adviser = User(email="role-adviser@university.edu.ng", password_hash=pwd, full_name="Role Adviser", role=UserRole.ADVISER)

        other_student_row = Student(
            matric_no="ROLE/24/00099", first_name="Other", last_name="Student", gender=Gender.MALE,
            date_of_birth=date(2003, 1, 1), department="Computer Science", programme="B.Sc. CS", level=100,
            entry_mode="UTME", entry_score=200, state_of_origin="Lagos", accommodation=Accommodation.ON_CAMPUS,
            enrolment_session="2024/2025",
        )
        session.add(other_student_row)
        session.commit()
        session.refresh(other_student_row)

        student_user = User(
            email="role-student@university.edu.ng", password_hash=pwd, full_name="Role Student",
            role=UserRole.STUDENT, student_id=other_student_row.id,
        )
        session.add_all([admin, lecturer, adviser, student_user])
        session.commit()
        for u in (admin, lecturer, adviser, student_user):
            session.refresh(u)
        users = {"admin": admin, "lecturer": lecturer, "adviser": adviser, "student": student_user}
        users["other_student_id"] = other_student_row.id
    return users
