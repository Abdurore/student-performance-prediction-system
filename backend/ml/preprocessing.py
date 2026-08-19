"""Raw-table loading and the shared preprocessing pipeline.

Loading is separated from feature engineering (ml/features.py) so the
same raw snapshot can be reused to build features for all three tasks
without re-querying the database three times. The preprocessing pipeline
is separated from training (Phase 3) so every one of the six algorithms
in Section G sees *identical* preprocessing -- a fair comparison is only
meaningful if the only thing that differs between runs is the algorithm.
"""

from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlmodel import Session

from app.db.session import engine

RAW_TABLE_QUERIES: dict[str, str] = {
    "students": "SELECT * FROM students",
    "courses": "SELECT * FROM courses",
    "enrolments": "SELECT * FROM enrolments",
    "attendance": "SELECT * FROM attendance",
    "engagement": "SELECT * FROM engagement",
    "academic_history": "SELECT * FROM academic_history",
}


def load_raw_tables() -> dict[str, pd.DataFrame]:
    """Read every table the feature pipeline needs into DataFrames.

    Reads directly from the database rather than the Phase 1 generator's
    in-memory dataset so this pipeline also works against real,
    CSV-imported institutional data (db/csv_import.py) with zero code
    changes -- the whole point of importing against the same schema.
    """
    with Session(engine) as session:
        connection = session.connection()
        return {name: pd.read_sql(query, connection) for name, query in RAW_TABLE_QUERIES.items()}


def build_preprocessing_pipeline(
    numeric_features: list[str], categorical_features: list[str]
) -> ColumnTransformer:
    """Build the shared preprocessing ColumnTransformer for all Phase 3 models.

    Median imputation for numeric columns: attendance/engagement carry
    genuine missingness (Phase 1's 4-8% injection) and academic scores are
    skewed rather than symmetric, so the median is a more robust fill
    value than the mean. Most-frequent imputation + one-hot encoding for
    categoricals, with unknown categories ignored at transform time so a
    category unseen in training (e.g. a new department) does not crash
    inference.
    """
    numeric_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ]
    )
