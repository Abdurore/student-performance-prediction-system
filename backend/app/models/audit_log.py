"""Append-only record of user actions for accountability and defence Q&A."""

from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.models.base import TimestampedModel


class AuditLog(TimestampedModel, table=True):
    __tablename__ = "audit_log"

    user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    action: str = Field(index=True)
    entity: str = Field(index=True)
    entity_id: int | None = Field(default=None, index=True)
    detail: dict | None = Field(default=None, sa_column=Column(JSON))
    timestamp: datetime
