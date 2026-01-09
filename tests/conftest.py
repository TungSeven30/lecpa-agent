"""Pytest fixtures for testing."""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Set test environment
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql://lecpa:lecpa_dev@localhost:5432/lecpa_agent_test")
os.environ.setdefault("S3_ENDPOINT", "http://localhost:9000")
os.environ.setdefault("S3_ACCESS_KEY", "minioadmin")
os.environ.setdefault("S3_SECRET_KEY", "minioadmin")
os.environ.setdefault("S3_BUCKET", "lecpa-documents-test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def golden_data_dir(project_root: Path) -> Path:
    """Get the golden test data directory."""
    return project_root / "tests" / "golden"


@pytest.fixture(scope="session")
def config_dir(project_root: Path) -> Path:
    """Get the config directory."""
    return project_root / "config"


@pytest.fixture
def db_session():
    """Create a database session for testing."""
    engine = create_engine(os.environ["DATABASE_URL"])
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_w2_path(golden_data_dir: Path) -> Path:
    """Get path to sample W-2 PDF."""
    return golden_data_dir / "w2_sample.pdf"


@pytest.fixture
def sample_1099_path(golden_data_dir: Path) -> Path:
    """Get path to sample 1099 PDF."""
    return golden_data_dir / "1099_sample.pdf"


@pytest.fixture
def sample_k1_path(golden_data_dir: Path) -> Path:
    """Get path to sample K-1 PDF."""
    return golden_data_dir / "k1_sample.pdf"


@pytest.fixture
def sample_notice_path(golden_data_dir: Path) -> Path:
    """Get path to sample scanned IRS notice PDF."""
    return golden_data_dir / "notice_scanned.pdf"
