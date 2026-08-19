"""Intervention business logic, scoped the same way student access is."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models import Intervention, User
from app.models.enums import InterventionStatus, UserRole
from app.services.student_service import scope_student_ids


def list_interventions(session: Session, current_user: User, student_id: int | None = None) -> list[Intervention]:
    query = select(Intervention)
    scope = scope_student_ids(session, current_user)
    if scope is not None:
        query = query.where(Intervention.student_id.in_(scope)) if scope else query.where(False)
    if student_id is not None:
        query = query.where(Intervention.student_id == student_id)
    return session.exec(query.order_by(Intervention.created_at.desc())).all()


def create_intervention(
    session: Session, current_user: User, student_id: int, prediction_id: int | None, action_type, notes: str | None
) -> Intervention:
    intervention = Intervention(
        student_id=student_id, prediction_id=prediction_id, created_by=current_user.id,
        action_type=action_type, notes=notes,
    )
    session.add(intervention)
    session.commit()
    session.refresh(intervention)
    return intervention


def update_intervention(
    session: Session, intervention: Intervention, status_value: InterventionStatus | None,
    notes: str | None, outcome_note: str | None,
) -> Intervention:
    if status_value is not None:
        intervention.status = status_value
        if status_value in (InterventionStatus.COMPLETED, InterventionStatus.CANCELLED):
            intervention.resolved_at = datetime.now(timezone.utc)
    if notes is not None:
        intervention.notes = notes
    if outcome_note is not None:
        intervention.outcome_note = outcome_note
    session.add(intervention)
    session.commit()
    session.refresh(intervention)
    return intervention


def can_manage_intervention(session: Session, current_user: User, intervention: Intervention) -> bool:
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.role == UserRole.ADVISER:
        scope = scope_student_ids(session, current_user)
        return scope is not None and intervention.student_id in scope
    return False
