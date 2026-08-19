"""Model registry endpoints: comparison, fairness, retrain, activate."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.deps import get_current_user, get_session, require_admin
from app.schemas.model_registry import (
    ActivateModelRequest,
    ModelComparisonResponse,
    ModelRegistryRead,
    RetrainRequest,
    RetrainResponse,
)
from app.services.model_service import activate_model, get_comparison, get_model_by_version, list_models, retrain

router = APIRouter(prefix="/models", tags=["models"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ModelRegistryRead])
def get_models(session: Session = Depends(get_session)) -> list:
    return list_models(session)


@router.get("/comparison", response_model=ModelComparisonResponse)
def get_models_comparison(session: Session = Depends(get_session)) -> ModelComparisonResponse:
    return ModelComparisonResponse(rows=get_comparison(session))


@router.get("/{version}/fairness")
def get_model_fairness(version: str, session: Session = Depends(get_session)) -> dict:
    model = get_model_by_version(session, version)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found.")
    if model.fairness_report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No fairness report generated for this model yet.")
    return model.fairness_report


@router.post("/retrain", response_model=RetrainResponse, dependencies=[Depends(require_admin)])
def post_retrain(payload: RetrainRequest) -> RetrainResponse:
    result = retrain(payload.tasks)
    return RetrainResponse(**result)


@router.post("/{version}/activate", response_model=ModelRegistryRead, dependencies=[Depends(require_admin)])
def post_activate(version: str, _payload: ActivateModelRequest | None = None, session: Session = Depends(get_session)):
    model = activate_model(session, version)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found.")
    return model
