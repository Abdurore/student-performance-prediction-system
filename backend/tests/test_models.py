"""Sanity checks on the SQLModel table definitions."""

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.models import User
from app.models.enums import UserRole


def test_create_all_tables_succeeds() -> None:
    """All eleven Section F tables -- including the circular users<->students FK -- create cleanly."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    expected = {
        "users", "students", "courses", "enrolments", "attendance", "engagement",
        "academic_history", "predictions", "interventions", "model_registry", "audit_log",
    }
    assert expected.issubset(set(SQLModel.metadata.tables.keys()))


def test_enum_columns_store_the_lowercase_value_not_the_member_name() -> None:
    """Guards against SQLAlchemy's Enum default of persisting the member NAME."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(email="a@b.com", password_hash="x", full_name="A B", role=UserRole.ADMIN))
        session.commit()

    with engine.connect() as conn:
        stored_role = conn.execute(text("select role from users")).scalar()
    assert stored_role == "admin"
