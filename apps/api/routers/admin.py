"""Admin-only router for administrative operations."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Document, DocumentChunk
from database.session import get_async_db
from shared.models.document import DocumentChunk as ChunkSchema

router = APIRouter()


class ChunkWithEmbedding(BaseModel):
    """Chunk with embedding data for admin viewing."""

    id: UUID
    document_id: UUID
    content: str
    page_start: int
    page_end: int
    chunk_index: int
    token_count: int | None
    section_header: str | None
    is_ocr: bool
    has_embedding: bool
    embedding_preview: list[float] | None = None  # First 10 values


@router.get("/documents/{document_id}/chunks", response_model=list[ChunkWithEmbedding])
async def get_document_chunks(
    document_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> list[ChunkWithEmbedding]:
    """Get all chunks for a document (admin-only).

    Returns chunk data including embedding status.
    """
    # Verify document exists
    result = await db.execute(select(Document).where(Document.id == document_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = result.scalars().all()

    return [
        ChunkWithEmbedding(
            id=chunk.id,
            document_id=chunk.document_id,
            content=chunk.content,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            chunk_index=chunk.chunk_index,
            token_count=chunk.token_count,
            section_header=chunk.section_header,
            is_ocr=chunk.is_ocr,
            has_embedding=chunk.embedding is not None,
            embedding_preview=chunk.embedding[:10] if chunk.embedding else None,
        )
        for chunk in chunks
    ]


class ReindexRequest(BaseModel):
    """Request to reindex documents."""

    document_ids: list[UUID] | None = None
    all_documents: bool = False


class ReindexResponse(BaseModel):
    """Response from reindex operation."""

    queued_count: int
    message: str


@router.post("/reindex", response_model=ReindexResponse)
async def reindex_documents(
    request: ReindexRequest,
    db: AsyncSession = Depends(get_async_db),
) -> ReindexResponse:
    """Queue documents for reindexing.

    Used when embedding model changes or to fix failed documents.
    """
    if not request.document_ids and not request.all_documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify document_ids or set all_documents=true",
        )

    if request.all_documents:
        result = await db.execute(select(Document.id))
        document_ids = [row[0] for row in result.all()]
    else:
        document_ids = request.document_ids or []

    # TODO: Queue reindex tasks via Celery

    return ReindexResponse(
        queued_count=len(document_ids),
        message=f"Queued {len(document_ids)} documents for reindexing",
    )
