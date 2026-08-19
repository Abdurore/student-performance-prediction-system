"""Aggregates every /api/v1 router."""

from fastapi import APIRouter

from app.api.v1 import analytics, auth, courses, interventions, models, predictions, reports, students

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(students.router)
api_router.include_router(courses.router)
api_router.include_router(predictions.router)
api_router.include_router(analytics.router)
api_router.include_router(models.router)
api_router.include_router(interventions.router)
api_router.include_router(reports.router)
