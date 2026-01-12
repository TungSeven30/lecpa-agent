"""SQLAlchemy database models."""

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Client(Base):
    """Client/taxpayer model."""

    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    # M2: NAS sync fields
    client_type: Mapped[str] = mapped_column(
        String(20), default="individual"
    )  # individual, business
    nas_folder_path: Mapped[str | None] = mapped_column(
        Text, index=True
    )  # Relative path on NAS
    approval_status: Mapped[str] = mapped_column(
        String(20), default="approved"
    )  # pending, approved, rejected
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    cases: Mapped[list["Case"]] = relationship(back_populates="client")
    # M2: Relationships to business entities (this client owns)
    owned_businesses: Mapped[list["ClientRelationship"]] = relationship(
        "ClientRelationship",
        foreign_keys="ClientRelationship.individual_id",
        back_populates="individual",
    )
    # M2: Relationships to individuals (for business clients)
    owners: Mapped[list["ClientRelationship"]] = relationship(
        "ClientRelationship",
        foreign_keys="ClientRelationship.business_id",
        back_populates="business",
    )


class Case(Base):
    """Tax case model."""

    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), index=True
    )
    tax_year: Mapped[int] = mapped_column(Integer, index=True)
    case_type: Mapped[str] = mapped_column(
        Enum(
            "tax_return",
            "notice",
            "correspondence",
            "amendment",
            "extension",
            "other",
            name="case_type_enum",
        ),
        default="tax_return",
    )
    status: Mapped[str] = mapped_column(
        Enum(
            "intake",
            "documents_pending",
            "in_progress",
            "review",
            "filed",
            "closed",
            name="case_status_enum",
        ),
        default="intake",
    )
    notes: Mapped[str | None] = mapped_column(Text)

    # M2: NAS sync fields
    is_permanent: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # For "Permanent" pseudo-case
    nas_year_path: Mapped[str | None] = mapped_column(Text)  # Path to year folder on NAS

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    client: Mapped["Client"] = relationship(back_populates="cases")
    documents: Mapped[list["Document"]] = relationship(back_populates="case")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="case")

    # Unique constraint: one case per client/year/type
    __table_args__ = (
        Index("ix_cases_client_year", "client_id", "tax_year"),
    )


class Document(Base):
    """Document model with processing status tracking."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)

    # Processing status tracking
    processing_status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "extracting",
            "ocr",
            "canonicalizing",
            "chunking",
            "embedding",
            "ready",
            "failed",
            name="processing_status_enum",
        ),
        default="pending",
        index=True,
    )
    processing_error: Mapped[str | None] = mapped_column(Text)
    is_ocr: Mapped[bool] = mapped_column(Boolean, default=False)

    # Embedding metadata for re-indexing support
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    embedding_dim: Mapped[int | None] = mapped_column(Integer)

    # Auto-detected tags
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # M2: NAS sync fields
    nas_relative_path: Mapped[str | None] = mapped_column(
        Text
    )  # Path relative to client folder
    nas_full_path: Mapped[str | None] = mapped_column(
        Text, unique=True, index=True
    )  # Full NAS path for dedup
    is_permanent: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # From Permanent folder
    folder_tag: Mapped[str | None] = mapped_column(
        String(50), index=True
    )  # tax_notice, transcript, etc.
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )  # Soft delete timestamp
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )  # Last seen during NAS scan
    file_hash: Mapped[str | None] = mapped_column(
        String(64), index=True
    )  # SHA256 hash for dedup

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    case: Mapped["Case"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    """Document chunk with embedding and full-text search support."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(Text)
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)
    token_count: Mapped[int | None] = mapped_column(Integer)
    section_header: Mapped[str | None] = mapped_column(String(255))
    is_ocr: Mapped[bool] = mapped_column(Boolean, default=False)

    # Vector embedding (dimension set based on model)
    # Using 384 for bge-small, change to 768 for bge-base
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))

    # Full-text search vector
    search_vector: Mapped[Any] = mapped_column(TSVECTOR)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="chunks")

    __table_args__ = (
        # GIN index for full-text search
        Index("ix_chunks_search_vector", "search_vector", postgresql_using="gin"),
        # Index for vector similarity search
        Index(
            "ix_chunks_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class Artifact(Base):
    """Generated artifact (emails, checklists, memos, etc.)."""

    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    artifact_type: Mapped[str] = mapped_column(
        Enum(
            "missing_docs_email",
            "organizer_checklist",
            "notice_response",
            "qc_memo",
            "extraction_result",
            "summary",
            "custom",
            name="artifact_type_enum",
        )
    )
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    content_format: Mapped[str] = mapped_column(String(20), default="markdown")
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    case: Mapped["Case"] = relationship(back_populates="artifacts")


class AuditLog(Base):
    """Audit log for tracking all system actions."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str | None] = mapped_column(String(255), index=True)
    user_email: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(50), index=True)
    resource_type: Mapped[str] = mapped_column(String(50), index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (
        Index("ix_audit_logs_created_at_desc", created_at.desc()),
    )


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    picture: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# =============================================================================
# M2: NAS Sync Models
# =============================================================================


class ClientRelationship(Base):
    """Track relationships between individual clients and business entities.

    Created automatically when .lnk shortcut files are detected during NAS sync.
    For example: An individual client folder containing "2010_Sim Sim Realty LLC.lnk"
    creates a relationship linking that individual to the business entity.
    """

    __tablename__ = "client_relationships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    individual_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        index=True,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(50), default="owner"
    )  # owner, partner, shareholder
    source: Mapped[str] = mapped_column(String(50))  # lnk_shortcut, manual
    source_path: Mapped[str | None] = mapped_column(Text)  # Path to .lnk file
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    individual: Mapped["Client"] = relationship(
        "Client",
        foreign_keys=[individual_id],
        back_populates="owned_businesses",
    )
    business: Mapped["Client"] = relationship(
        "Client",
        foreign_keys=[business_id],
        back_populates="owners",
    )

    __table_args__ = (
        Index(
            "ix_client_rel_unique",
            "individual_id",
            "business_id",
            unique=True,
        ),
    )


class SyncQueueItem(Base):
    """Queue for new clients/cases detected by NAS sync that need admin approval.

    When the sync agent detects a new client folder or year folder, it creates
    a queue item that must be approved before documents can be ingested.
    Items can be auto-approved after a configurable delay (default 4 hours).
    """

    __tablename__ = "sync_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    item_type: Mapped[str] = mapped_column(String(20))  # client, case
    nas_path: Mapped[str] = mapped_column(Text, unique=True)  # Full path on NAS
    parsed_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB
    )  # Extracted info (code, name, year, type)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending, approved, rejected, auto_approved
    auto_approve_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )  # When to auto-approve
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(Text)


class SyncDigest(Base):
    """Daily digest of NAS sync activity for email notifications.

    Tracks statistics for each day's sync activity including:
    - Files processed and failed
    - New clients and cases detected
    - Items pending approval
    """

    __tablename__ = "sync_digest"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    digest_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), unique=True
    )  # Date of digest (day)
    files_processed: Mapped[int] = mapped_column(Integer, default=0)
    files_failed: Mapped[int] = mapped_column(Integer, default=0)
    new_clients: Mapped[int] = mapped_column(Integer, default=0)
    new_cases: Mapped[int] = mapped_column(Integer, default=0)
    items_pending_approval: Mapped[int] = mapped_column(Integer, default=0)
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
