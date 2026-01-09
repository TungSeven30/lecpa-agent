"""Search router with hybrid vector + full-text search."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_async_db
from services.search import HybridSearchService, get_search_service
from shared.models.document import Citation

router = APIRouter()


class SearchQuery(BaseModel):
    """Search query parameters."""

    query: str = Field(min_length=1, max_length=1000)
    client_code: str | None = None
    case_id: UUID | None = None
    doc_types: list[str] | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    vector_weight: float = Field(default=0.7, ge=0, le=1)
    fts_weight: float = Field(default=0.3, ge=0, le=1)


class SearchResult(BaseModel):
    """Search result with citations."""

    query: str
    total_results: int
    citations: list[Citation]


@router.post("", response_model=SearchResult)
async def search_documents(
    search_query: SearchQuery,
    db: AsyncSession = Depends(get_async_db),
    search_service: HybridSearchService = Depends(get_search_service),
) -> SearchResult:
    """Search documents using hybrid vector + full-text search.

    The search combines:
    - pgvector cosine similarity for semantic search
    - Postgres tsvector full-text search for keyword matching

    Final score = vector_score * vector_weight + fts_score * fts_weight
    """
    citations = await search_service.search(
        query=search_query.query,
        client_code=search_query.client_code,
        case_id=search_query.case_id,
        doc_types=search_query.doc_types,
        top_k=search_query.top_k,
        vector_weight=search_query.vector_weight,
        fts_weight=search_query.fts_weight,
    )

    return SearchResult(
        query=search_query.query,
        total_results=len(citations),
        citations=citations,
    )
