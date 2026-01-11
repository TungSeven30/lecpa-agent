"""Document-related Pydantic models."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentProcessingStatus(str, Enum):
    """Document processing pipeline status."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    OCR = "ocr"
    CANONICALIZING = "canonicalizing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


class DocumentTag(str, Enum):
    """Auto-detected document tags."""

    W2 = "W2"
    FORM_1099 = "1099"
    K1 = "K1"
    FORM_1040 = "1040"
    SCHEDULE = "SCHEDULE"
    IRS_NOTICE = "IRS_NOTICE"
    BANK_STATEMENT = "BANK_STATEMENT"
    BROKERAGE = "BROKERAGE"
    ORGANIZER = "ORGANIZER"
    ENGAGEMENT_LETTER = "ENGAGEMENT_LETTER"
    OTHER = "OTHER"


class Document(BaseModel):
    """Document metadata model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: UUID
    filename: str
    original_filename: str
    storage_key: str
    mime_type: str
    file_size: int
    page_count: int | None = None
    is_ocr: bool = False
    processing_status: DocumentProcessingStatus = DocumentProcessingStatus.PENDING
    processing_error: str | None = None
    embedding_model: str | None = None
    embedding_dim: int | None = None
    tags: list[DocumentTag] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DocumentChunk(BaseModel):
    """Document chunk model for RAG retrieval."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    content: str
    page_start: int
    page_end: int
    chunk_index: int
    token_count: int | None = None
    section_header: str | None = None
    is_ocr: bool = False
    created_at: datetime


class Citation(BaseModel):
    """Citation reference for RAG responses."""

    document_id: UUID
    document_filename: str
    chunk_id: UUID
    page_start: int
    page_end: int
    snippet: str = Field(max_length=500)
    relevance_score: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1)


class DocumentCreate(BaseModel):
    """Schema for creating a new document."""

    case_id: UUID
    filename: str
    mime_type: str
    file_size: int
    tags: list[DocumentTag] = Field(default_factory=list)


class DocumentUpdate(BaseModel):
    """Schema for updating document status."""

    processing_status: DocumentProcessingStatus | None = None
    processing_error: str | None = None
    page_count: int | None = None
    is_ocr: bool | None = None
    embedding_model: str | None = None
    embedding_dim: int | None = None
    tags: list[DocumentTag] | None = None
