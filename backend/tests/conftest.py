"""Shared fixtures: a small synthetic dataset loaded into an isolated temp DB.

Used by test_features.py, test_train.py, test_explain.py, and
test_fairness.py so none of them depend on `make seed` having been run
against the shared demo database.
"""

from datetime import datetime, timezone

import joblib
import pytest
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline
from sqlmodel import Session, SQLModel, create_engine

from app.db import seed as seed_module
from app.models import AcademicHistory, Attendance, Course, Engagement, Enrolment, ModelRegistry, Student, User
from ml import preprocessing
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
    """Fit + register one plain (untuned) model each for T1 and T2 directly,
    bypassing ml.train's GridSearchCV/SMOTE machinery -- explain.py and
    fairness.py only need *an* active model per task, and fitting one
    pipeline directly is far faster than a full train_task() run."""
    X, y_df, _meta = build_semester_features(raw_tables)
    numeric_cols, categorical_cols = column_types(X)
    artifacts_dir = tmp_path_factory.mktemp("explain_fairness_artifacts")

    specs = (
        ("risk_classification", "logistic_regression", LogisticRegression(max_iter=1000), y_df["risk_label"]),
        ("gpa_regression", "linear_regression", LinearRegression(), y_df["target_gpa"]),
    )
    with Session(small_db_engine) as session:
        for task, algo, estimator, y in specs:
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
