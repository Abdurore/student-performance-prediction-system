"""Shared mixin so every table gets an id and audit timestamps."""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp for default/onupdate hooks."""
    return datetime.now(timezone.utc)


class TimestampedModel(SQLModel):
    """Base class providing id, created_at, and updated_at to every table."""

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": utcnow},
    )
