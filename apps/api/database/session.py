"""Database session configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file before accessing environment variables
_env_file = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(_env_file)

from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker


def get_database_url() -> str:
    """Get the database URL from environment."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable not set")
    return url


def get_async_database_url() -> str:
    """Get the async database URL from environment."""
    url = os.environ.get("DATABASE_URL_ASYNC")
    if url:
        return url

    # Convert sync URL to async
    sync_url = get_database_url()
    if sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return sync_url


# Synchronous engine (for migrations and sync operations)
engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Async engine (for FastAPI endpoints)
async_engine = create_async_engine(
    get_async_database_url(),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Session factories
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency for synchronous database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
