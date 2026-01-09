"""Hybrid search service combining vector and full-text search."""

from functools import lru_cache
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Client, Document, DocumentChunk, Case
from database.session import get_async_db
from services.embedding_provider import EmbeddingProvider, get_embedding_provider
from shared.models.document import Citation


class HybridSearchService:
    """Service for hybrid vector + full-text search."""

    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        """Initialize the search service.

        Args:
            embedding_provider: Provider for generating query embeddings
        """
        self.embedding_provider = embedding_provider

    async def search(
        self,
        query: str,
        db: AsyncSession,
        client_code: str | None = None,
        case_id: UUID | None = None,
        doc_types: list[str] | None = None,
        top_k: int = 10,
        vector_weight: float = 0.7,
        fts_weight: float = 0.3,
    ) -> list[Citation]:
        """Search documents using hybrid vector + full-text search.

        Args:
            query: Search query
            db: Database session
            client_code: Filter by client code
            case_id: Filter by case ID
            doc_types: Filter by document types/tags
            top_k: Number of results to return
            vector_weight: Weight for vector similarity (0-1)
            fts_weight: Weight for full-text search (0-1)

        Returns:
            List of citations sorted by combined score
        """
        # Generate query embedding
        query_embedding = await self.embedding_provider.embed([query])
        query_vector = query_embedding[0]

        # Build the hybrid search query
        # Vector similarity: 1 - cosine distance (pgvector uses <=> for cosine distance)
        # FTS score: ts_rank
        vector_score = (1 - DocumentChunk.embedding.cosine_distance(query_vector)).label(
            "vector_score"
        )
        fts_score = func.ts_rank(
            DocumentChunk.search_vector,
            func.plainto_tsquery("english", query),
        ).label("fts_score")

        # Combined score
        combined_score = (
            vector_score * vector_weight + fts_score * fts_weight
        ).label("score")

        # Base query
        stmt = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                DocumentChunk.content,
                DocumentChunk.page_start,
                DocumentChunk.page_end,
                Document.filename,
                combined_score,
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .join(Case, Document.case_id == Case.id)
            .where(Document.processing_status == "ready")
            .where(DocumentChunk.embedding.isnot(None))
        )

        # Apply filters
        if case_id:
            stmt = stmt.where(Document.case_id == case_id)

        if client_code:
            stmt = stmt.join(Client, Case.client_id == Client.id).where(
                Client.client_code == client_code
            )

        if doc_types:
            stmt = stmt.where(Document.tags.overlap(doc_types))

        # Order by combined score and limit
        stmt = stmt.order_by(text("score DESC")).limit(top_k)

        result = await db.execute(stmt)
        rows = result.all()

        # Convert to citations
        citations = []
        for rank, row in enumerate(rows, 1):
            citations.append(
                Citation(
                    document_id=row.document_id,
                    document_filename=row.filename,
                    chunk_id=row.id,
                    page_start=row.page_start,
                    page_end=row.page_end,
                    snippet=row.content[:500] if len(row.content) > 500 else row.content,
                    relevance_score=min(1.0, max(0.0, float(row.score))),
                    rank=rank,
                )
            )

        return citations


@lru_cache
def get_search_service() -> HybridSearchService:
    """Get cached search service instance."""
    return HybridSearchService(get_embedding_provider())
