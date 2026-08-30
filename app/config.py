"""
Configuration management for SubLedger backend.
Handles environment variables and application settings.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite:///./database.db"

    # Environment
    environment: str = "development"
    log_level: str = "INFO"

    # API
    api_title: str = "SubLedger API"
    api_version: str = "1.0.0"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
