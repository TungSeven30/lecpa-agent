"""M2: NAS sync schema changes.

Add columns and tables to support NAS filesystem synchronization:
- Client: client_type, nas_folder_path, approval_status, approved_at, approved_by
- Case: is_permanent, nas_year_path
- Document: nas_relative_path, nas_full_path, is_permanent, folder_tag, deleted_at,
            last_seen_at, file_hash
- New tables: client_relationships, sync_queue, sync_digest

Revision ID: 003_m2_nas_sync
Revises: 002_rename_s3_key_to_storage_key
Create Date: 2025-01-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_m2_nas_sync"
down_revision: Union[str, None] = "002_rename_s3_key_to_storage_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply M2 NAS sync schema changes."""
    # ==========================================================================
    # Add columns to clients table
    # ==========================================================================
    op.add_column(
        "clients",
        sa.Column("client_type", sa.String(20), nullable=False, server_default="individual"),
    )
    op.add_column(
        "clients",
        sa.Column("nas_folder_path", sa.Text(), nullable=True),
    )
    op.add_column(
        "clients",
        sa.Column("approval_status", sa.String(20), nullable=False, server_default="approved"),
    )
    op.add_column(
        "clients",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "clients",
        sa.Column(
            "approved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_clients_nas_folder_path", "clients", ["nas_folder_path"])

    # ==========================================================================
    # Add columns to cases table
    # ==========================================================================
    op.add_column(
        "cases",
        sa.Column("is_permanent", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "cases",
        sa.Column("nas_year_path", sa.Text(), nullable=True),
    )

    # ==========================================================================
    # Add columns to documents table
    # ==========================================================================
    op.add_column(
        "documents",
        sa.Column("nas_relative_path", sa.Text(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("nas_full_path", sa.Text(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("is_permanent", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "documents",
        sa.Column("folder_tag", sa.String(50), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "documents",
        sa.Column("file_hash", sa.String(64), nullable=True),
    )
    op.create_index("ix_documents_nas_full_path", "documents", ["nas_full_path"], unique=True)
    op.create_index("ix_documents_folder_tag", "documents", ["folder_tag"])
    op.create_index("ix_documents_deleted_at", "documents", ["deleted_at"])
    op.create_index("ix_documents_file_hash", "documents", ["file_hash"])

    # ==========================================================================
    # Create client_relationships table
    # ==========================================================================
    op.create_table(
        "client_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "individual_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "business_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(50), nullable=False, server_default="owner"),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_client_rel_individual", "client_relationships", ["individual_id"])
    op.create_index("ix_client_rel_business", "client_relationships", ["business_id"])
    op.create_index(
        "ix_client_rel_unique",
        "client_relationships",
        ["individual_id", "business_id"],
        unique=True,
    )

    # ==========================================================================
    # Create sync_queue table
    # ==========================================================================
    op.create_table(
        "sync_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_type", sa.String(20), nullable=False),
        sa.Column("nas_path", sa.Text(), nullable=False, unique=True),
        sa.Column("parsed_data", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("auto_approve_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "reviewed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_sync_queue_status", "sync_queue", ["status"])
    op.create_index("ix_sync_queue_created_at", "sync_queue", ["created_at"])

    # ==========================================================================
    # Create sync_digest table
    # ==========================================================================
    op.create_table(
        "sync_digest",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("digest_date", sa.DateTime(timezone=True), nullable=False, unique=True),
        sa.Column("files_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_clients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_cases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_pending_approval", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_details", postgresql.JSONB(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    """Revert M2 NAS sync schema changes."""
    # Drop new tables
    op.drop_table("sync_digest")
    op.drop_table("sync_queue")
    op.drop_table("client_relationships")

    # Drop document columns and indexes
    op.drop_index("ix_documents_file_hash", table_name="documents")
    op.drop_index("ix_documents_deleted_at", table_name="documents")
    op.drop_index("ix_documents_folder_tag", table_name="documents")
    op.drop_index("ix_documents_nas_full_path", table_name="documents")
    op.drop_column("documents", "file_hash")
    op.drop_column("documents", "last_seen_at")
    op.drop_column("documents", "deleted_at")
    op.drop_column("documents", "folder_tag")
    op.drop_column("documents", "is_permanent")
    op.drop_column("documents", "nas_full_path")
    op.drop_column("documents", "nas_relative_path")

    # Drop case columns
    op.drop_column("cases", "nas_year_path")
    op.drop_column("cases", "is_permanent")

    # Drop client columns and indexes
    op.drop_index("ix_clients_nas_folder_path", table_name="clients")
    op.drop_column("clients", "approved_by")
    op.drop_column("clients", "approved_at")
    op.drop_column("clients", "approval_status")
    op.drop_column("clients", "nas_folder_path")
    op.drop_column("clients", "client_type")
