"""Application configuration."""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Application
    app_name: str = "Krystal Le Agent API"
    environment: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = "postgresql://lecpa:lecpa_dev@localhost:5432/lecpa_agent"
    database_url_async: str = (
        "postgresql+asyncpg://lecpa:lecpa_dev@localhost:5432/lecpa_agent"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Object Storage (MinIO/S3)
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "lecpa-documents"
    s3_region: str = "us-east-1"

    # Authentication
    google_client_id: str = ""
    google_client_secret: str = ""
    allowed_email_domains: list[str] = []

    # LLM
    anthropic_api_key: str = ""

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience accessor
settings = get_settings()
