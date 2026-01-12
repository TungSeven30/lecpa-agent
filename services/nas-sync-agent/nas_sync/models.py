"""Pydantic models for NAS sync agent."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ParsedPath(BaseModel):
    """Result of parsing a NAS file path."""

    client_code: str | None = None
    client_name: str | None = None
    client_type: str | None = None  # individual or business
    year: int | None = None
    folder_tag: str | None = None
    is_permanent: bool = False
    relative_path: str = ""
    detected_tags: list[str] = Field(default_factory=list)
    is_valid: bool = False
    skip_reason: str | None = None


class FileArrivedRequest(BaseModel):
    """Request body for POST /ingest/file-arrived."""

    nas_path: str
    file_size: int
    file_hash: str
    modified_time: datetime
    parsed_info: ParsedPath


class FileDeletedRequest(BaseModel):
    """Request body for POST /ingest/file-deleted."""

    nas_path: str


class FileArrivedResponse(BaseModel):
    """Response from POST /ingest/file-arrived."""

    status: str  # queued, pending_approval, duplicate, error
    document_id: str | None = None
    queue_item_id: str | None = None
    existing_document_id: str | None = None
    message: str


class FileDeletedResponse(BaseModel):
    """Response from POST /ingest/file-deleted."""

    status: str  # soft_deleted, not_found, error
    document_id: str | None = None
    retention_until: datetime | None = None
    message: str


class SyncQueueItem(BaseModel):
    """Queue item returned from GET /ingest/sync-queue."""

    id: str
    item_type: str  # client, case
    nas_path: str
    parsed_data: dict[str, Any]
    status: str
    created_at: datetime
    auto_approve_at: datetime | None = None


class SyncStatus(BaseModel):
    """Sync status returned from GET /ingest/sync-status."""

    agent_status: str
    last_heartbeat: datetime | None = None
    last_file_event: datetime | None = None
    queue_stats: dict[str, int]
    today_stats: dict[str, int]


class ClientPattern(BaseModel):
    """Pattern for matching client folder names."""

    pattern: str
    type: str  # individual or business


class SpecialFolder(BaseModel):
    """Configuration for special folders."""

    folder: str
    tag: str
    is_permanent: bool = False


class DocumentTagPattern(BaseModel):
    """Pattern for auto-tagging documents."""

    pattern: str
    tag: str


class NASConfig(BaseModel):
    """NAS-related configuration."""

    root_path: str
    watch_recursive: bool = True
    debounce_seconds: float = 2.0


class APIConfig(BaseModel):
    """API client configuration."""

    base_url: str
    api_key: str
    timeout_seconds: int = 30
    retry_attempts: int = 3


class ParsingConfig(BaseModel):
    """Folder parsing configuration."""

    client_patterns: list[ClientPattern]
    year_pattern: str
    special_folders: list[SpecialFolder]
    skip_patterns: list[str]
    document_tags: list[DocumentTagPattern]


class StateConfig(BaseModel):
    """Local state configuration."""

    db_path: str


class SMTPConfig(BaseModel):
    """SMTP configuration for digest emails."""

    host: str
    port: int = 587
    user: str
    password: str


class DigestConfig(BaseModel):
    """Digest email configuration."""

    enabled: bool = True
    send_time: str = "08:00"
    recipients: list[str]
    smtp: SMTPConfig


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"


class Config(BaseModel):
    """Full configuration for the NAS sync agent."""

    nas: NASConfig
    api: APIConfig
    parsing: ParsingConfig
    state: StateConfig
    digest: DigestConfig
    logging: LoggingConfig
