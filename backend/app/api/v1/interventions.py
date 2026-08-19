"""Intervention CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.deps import get_current_user, get_session, require_admin_or_adviser
from app.models import Intervention, User
from app.schemas.intervention import InterventionCreate, InterventionRead, InterventionUpdate
from app.services.intervention_service import can_manage_intervention, create_intervention, list_interventions, update_intervention

router = APIRouter(prefix="/interventions", tags=["interventions"])


@router.get("", response_model=list[InterventionRead])
def get_interventions(
    student_id: int | None = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[Intervention]:
    return list_interventions(session, current_user, student_id)


@router.post("", response_model=InterventionRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin_or_adviser)])
def post_intervention(
    payload: InterventionCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Intervention:
    return create_intervention(
        session, current_user, payload.student_id, payload.prediction_id, payload.action_type, payload.notes
    )


@router.put("/{intervention_id}", response_model=InterventionRead, dependencies=[Depends(require_admin_or_adviser)])
def put_intervention(
    intervention_id: int,
    payload: InterventionUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Intervention:
    intervention = session.get(Intervention, intervention_id)
    if intervention is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intervention not found.")
    if not can_manage_intervention(session, current_user, intervention):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may not update this intervention.")
    return update_intervention(session, intervention, payload.status, payload.notes, payload.outcome_note)
