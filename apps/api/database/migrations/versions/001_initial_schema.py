"""Initial database schema.

Revision ID: 001
Revises:
Create Date: 2026-01-09

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create enum types
    op.execute("""
        CREATE TYPE case_type_enum AS ENUM (
            'tax_return', 'notice', 'correspondence', 'amendment', 'extension', 'other'
        )
    """)
    op.execute("""
        CREATE TYPE case_status_enum AS ENUM (
            'intake', 'documents_pending', 'in_progress', 'review', 'filed', 'closed'
        )
    """)
    op.execute("""
        CREATE TYPE processing_status_enum AS ENUM (
            'pending', 'extracting', 'ocr', 'canonicalizing', 'chunking', 'embedding', 'ready', 'failed'
        )
    """)
    op.execute("""
        CREATE TYPE artifact_type_enum AS ENUM (
            'missing_docs_email', 'organizer_checklist', 'notice_response', 'qc_memo',
            'extraction_result', 'summary', 'custom'
        )
    """)

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("picture", sa.String(512)),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("is_admin", sa.Boolean(), default=False),
        sa.Column("last_login", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # Create clients table
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_code", sa.String(10), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("address", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_clients_client_code", "clients", ["client_code"])

    # Create cases table
    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column(
            "case_type",
            postgresql.ENUM(
                "tax_return",
                "notice",
                "correspondence",
                "amendment",
                "extension",
                "other",
                name="case_type_enum",
                create_type=False,
            ),
            default="tax_return",
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "intake",
                "documents_pending",
                "in_progress",
                "review",
                "filed",
                "closed",
                name="case_status_enum",
                create_type=False,
            ),
            default="intake",
        ),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_cases_client_id", "cases", ["client_id"])
    op.create_index("ix_cases_tax_year", "cases", ["tax_year"])
    op.create_index("ix_cases_client_year", "cases", ["client_id", "tax_year"])

    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("s3_key", sa.String(512), unique=True, nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer()),
        sa.Column("sha256", sa.String(64)),
        sa.Column(
            "processing_status",
            postgresql.ENUM(
                "pending",
                "extracting",
                "ocr",
                "canonicalizing",
                "chunking",
                "embedding",
                "ready",
                "failed",
                name="processing_status_enum",
                create_type=False,
            ),
            default="pending",
        ),
        sa.Column("processing_error", sa.Text()),
        sa.Column("is_ocr", sa.Boolean(), default=False),
        sa.Column("embedding_model", sa.String(100)),
        sa.Column("embedding_dim", sa.Integer()),
        sa.Column("tags", postgresql.ARRAY(sa.String()), default=[]),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_documents_case_id", "documents", ["case_id"])
    op.create_index("ix_documents_sha256", "documents", ["sha256"])
    op.create_index("ix_documents_processing_status", "documents", ["processing_status"])

    # Create document_chunks table
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer()),
        sa.Column("section_header", sa.String(255)),
        sa.Column("is_ocr", sa.Boolean(), default=False),
        sa.Column("embedding", Vector(384)),  # bge-small dimension
        sa.Column("search_vector", postgresql.TSVECTOR()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    # Create GIN index for full-text search
    op.execute("""
        CREATE INDEX ix_chunks_search_vector ON document_chunks
        USING GIN (search_vector)
    """)

    # Create IVFFlat index for vector similarity (requires data first, so create later)
    # This will be created after initial data is loaded

    # Create artifacts table
    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "artifact_type",
            postgresql.ENUM(
                "missing_docs_email",
                "organizer_checklist",
                "notice_response",
                "qc_memo",
                "extraction_result",
                "summary",
                "custom",
                name="artifact_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_format", sa.String(20), default="markdown"),
        sa.Column("version", sa.Integer(), default=1),
        sa.Column("is_draft", sa.Boolean(), default=True),
        sa.Column("created_by", sa.String(255)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_artifacts_case_id", "artifacts", ["case_id"])

    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(255)),
        sa.Column("user_email", sa.String(255)),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True)),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("audit_logs")
    op.drop_table("artifacts")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("cases")
    op.drop_table("clients")
    op.drop_table("users")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS artifact_type_enum")
    op.execute("DROP TYPE IF EXISTS processing_status_enum")
    op.execute("DROP TYPE IF EXISTS case_status_enum")
    op.execute("DROP TYPE IF EXISTS case_type_enum")
