"""Database engine and session management.

Defaults to a local SQLite file; switching to PostgreSQL is a one-line
change to DATABASE_URL (see app/core/config.py), per the project's
hard constraint of a single-env-var database swap.
"""

from collections.abc import Iterator

from sqlmodel import Session, create_engine

from app.core.config import get_settings

settings = get_settings()
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=_connect_args)


def get_session() -> Iterator[Session]:
    """Yield a request-scoped session for FastAPI dependency injection."""
    with Session(engine) as session:
        yield session
