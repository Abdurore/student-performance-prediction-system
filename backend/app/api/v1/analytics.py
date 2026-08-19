"""Analytics dashboard endpoints -- every figure computed live, never mocked."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.deps import get_current_user, get_session
from app.schemas.analytics import CorrelationsResponse, CourseDifficultyResponse, OverviewResponse, TrendsResponse
from app.services.analytics_service import get_correlations, get_course_difficulty, get_overview, get_trends

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(get_current_user)])


@router.get("/overview", response_model=OverviewResponse)
def overview(session: Session = Depends(get_session)) -> OverviewResponse:
    return get_overview(session)


@router.get("/trends", response_model=TrendsResponse)
def trends(session: Session = Depends(get_session)) -> TrendsResponse:
    return get_trends(session)


@router.get("/correlations", response_model=CorrelationsResponse)
def correlations() -> CorrelationsResponse:
    return get_correlations()


@router.get("/course-difficulty", response_model=CourseDifficultyResponse)
def course_difficulty(session: Session = Depends(get_session)) -> CourseDifficultyResponse:
    return get_course_difficulty(session)
