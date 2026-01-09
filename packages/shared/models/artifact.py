"""Artifact Pydantic models for generated outputs."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ArtifactType(str, Enum):
    """Type of generated artifact."""

    MISSING_DOCS_EMAIL = "missing_docs_email"
    ORGANIZER_CHECKLIST = "organizer_checklist"
    NOTICE_RESPONSE = "notice_response"
    QC_MEMO = "qc_memo"
    EXTRACTION_RESULT = "extraction_result"
    SUMMARY = "summary"
    CUSTOM = "custom"


class Artifact(BaseModel):
    """Generated artifact model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: UUID
    artifact_type: ArtifactType
    title: str
    content: str
    content_format: str = "markdown"  # markdown, json, html
    version: int = 1
    is_draft: bool = True
    created_by: str | None = None  # user email or "system"
    created_at: datetime
    updated_at: datetime


class ArtifactCreate(BaseModel):
    """Schema for creating a new artifact."""

    case_id: UUID
    artifact_type: ArtifactType
    title: str
    content: str
    content_format: str = "markdown"
    is_draft: bool = True


class ArtifactUpdate(BaseModel):
    """Schema for updating an artifact."""

    title: str | None = None
    content: str | None = None
    is_draft: bool | None = None


class ArtifactVersion(BaseModel):
    """Artifact version history entry."""

    artifact_id: UUID
    version: int
    content: str
    created_by: str | None = None
    created_at: datetime


class ArtifactSummary(BaseModel):
    """Summary of artifact for list views."""

    id: UUID
    case_id: UUID
    artifact_type: ArtifactType
    title: str
    version: int
    is_draft: bool
    updated_at: datetime
