"""Environment-backed application settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from an optional local .env file."""

    app_name: str = "Student Performance Prediction System"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    database_url: str = "sqlite:///./student_performance.db"
    secret_key: str = Field("replace-this-before-production", min_length=16)
    access_token_expire_minutes: int = 60
    cors_origins: list[str] = ["http://localhost:5173"]
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """Cache settings so all request handlers use the same configuration."""
    return Settings()
