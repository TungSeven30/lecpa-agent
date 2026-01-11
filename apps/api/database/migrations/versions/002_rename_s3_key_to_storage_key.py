"""Rename s3_key to storage_key for storage backend abstraction.

Revision ID: 002_rename_s3_key
Revises: 001_initial_schema
Create Date: 2026-01-10

This migration supports the transition from S3-specific naming to
a generic storage key that works with multiple backends (filesystem, S3, etc.).
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_rename_s3_key"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename s3_key column to storage_key in documents table."""
    op.alter_column("documents", "s3_key", new_column_name="storage_key")


def downgrade() -> None:
    """Revert storage_key column back to s3_key."""
    op.alter_column("documents", "storage_key", new_column_name="s3_key")
