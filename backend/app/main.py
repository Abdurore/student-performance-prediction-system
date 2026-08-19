"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", description="Offline-first student performance prediction platform.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Provide a dependency-free readiness check for local development."""
    return {"status": "ok", "environment": settings.environment}
