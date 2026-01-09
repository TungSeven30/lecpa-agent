"""Audit logging Pydantic models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditAction(str, Enum):
    """Auditable actions in the system."""

    # Document actions
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_VIEWED = "document.viewed"
    DOCUMENT_DOWNLOADED = "document.downloaded"
    DOCUMENT_DELETED = "document.deleted"
    DOCUMENT_PROCESSING_STARTED = "document.processing_started"
    DOCUMENT_PROCESSING_COMPLETED = "document.processing_completed"
    DOCUMENT_PROCESSING_FAILED = "document.processing_failed"

    # Search actions
    SEARCH_EXECUTED = "search.executed"
    SEARCH_RESULTS_VIEWED = "search.results_viewed"

    # Chat actions
    CHAT_MESSAGE_SENT = "chat.message_sent"
    CHAT_RESPONSE_GENERATED = "chat.response_generated"

    # Case actions
    CASE_CREATED = "case.created"
    CASE_UPDATED = "case.updated"
    CASE_CLOSED = "case.closed"

    # Artifact actions
    ARTIFACT_CREATED = "artifact.created"
    ARTIFACT_UPDATED = "artifact.updated"
    ARTIFACT_EXPORTED = "artifact.exported"
    ARTIFACT_DELETED = "artifact.deleted"

    # Auth actions
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"


class AuditLog(BaseModel):
    """Audit log entry model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str | None = None  # email or "system"
    user_email: str | None = None
    action: AuditAction
    resource_type: str  # document, case, artifact, search, chat
    resource_id: UUID | None = None
    metadata: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime


class AuditLogCreate(BaseModel):
    """Schema for creating an audit log entry."""

    user_id: str | None = None
    user_email: str | None = None
    action: AuditAction
    resource_type: str
    resource_id: UUID | None = None
    metadata: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None


class AuditLogQuery(BaseModel):
    """Query parameters for audit log search."""

    user_id: str | None = None
    action: AuditAction | None = None
    resource_type: str | None = None
    resource_id: UUID | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    limit: int = 100
    offset: int = 0
