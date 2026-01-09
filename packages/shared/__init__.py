"""Shared models, schemas, and utilities for Krystal Le Agent."""

from shared.models.document import (
    Citation,
    Document,
    DocumentChunk,
    DocumentProcessingStatus,
    DocumentTag,
)
from shared.models.case import Case, CaseStatus, CaseType, Client
from shared.models.artifact import Artifact, ArtifactType
from shared.models.audit import AuditAction, AuditLog
from shared.models.agent_outputs import (
    ExtractionResult,
    FirmKnowledgeResponse,
    MissingDocsEmail,
    NoticeResponse,
    QCReport,
)

__all__ = [
    # Document models
    "Citation",
    "Document",
    "DocumentChunk",
    "DocumentProcessingStatus",
    "DocumentTag",
    # Case models
    "Case",
    "CaseStatus",
    "CaseType",
    "Client",
    # Artifact models
    "Artifact",
    "ArtifactType",
    # Audit models
    "AuditAction",
    "AuditLog",
    # Agent output models
    "ExtractionResult",
    "FirmKnowledgeResponse",
    "MissingDocsEmail",
    "NoticeResponse",
    "QCReport",
]
