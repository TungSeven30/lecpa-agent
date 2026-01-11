"""Main document ingestion orchestration task."""

import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Add packages to path for storage backend imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "api"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "packages"))

from services.storage import StorageBackend, get_storage
from shared.config import load_embeddings_config

from main import app
from tasks.extract import get_extractor
from tasks.ocr import check_ocr_needed

logger = structlog.get_logger()


def get_db_session() -> Session:
    """Get a database session."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not set")
    engine = create_engine(database_url)
    return Session(engine)


def get_storage_backend() -> StorageBackend:
    """Get the configured storage backend.

    Returns:
        Configured storage backend instance (filesystem, S3, etc.)
    """
    return get_storage()


def update_document_status(
    db: Session,
    document_id: str,
    status: str,
    error: str | None = None,
    **kwargs: Any,
) -> None:
    """Update document processing status.

    Args:
        db: Database session
        document_id: Document ID
        status: New status
        error: Error message if failed
        **kwargs: Additional fields to update
    """
    updates = {"processing_status": status}
    if error:
        updates["processing_error"] = error
    updates.update(kwargs)

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["doc_id"] = document_id

    db.execute(
        text(f"UPDATE documents SET {set_clause}, updated_at = NOW() WHERE id = :doc_id"),
        updates,
    )
    db.commit()


def store_chunks(
    db: Session,
    document_id: str,
    chunks: list[dict],
) -> None:
    """Store document chunks with embeddings.

    Args:
        db: Database session
        document_id: Document ID
        chunks: List of chunk dicts with embeddings
    """
    for chunk in chunks:
        chunk_id = str(uuid.uuid4())
        embedding = chunk["embedding"]

        # Generate tsvector for full-text search
        db.execute(
            text("""
                INSERT INTO document_chunks (
                    id, document_id, content, page_start, page_end,
                    chunk_index, token_count, section_header, is_ocr,
                    embedding, search_vector, created_at
                ) VALUES (
                    :id, :document_id, :content, :page_start, :page_end,
                    :chunk_index, :token_count, :section_header, :is_ocr,
                    :embedding, to_tsvector('english', :content), NOW()
                )
            """),
            {
                "id": chunk_id,
                "document_id": document_id,
                "content": chunk["content"],
                "page_start": chunk["page_start"],
                "page_end": chunk["page_end"],
                "chunk_index": chunk["chunk_index"],
                "token_count": chunk.get("token_count"),
                "section_header": chunk.get("section_header"),
                "is_ocr": chunk.get("is_ocr", False),
                "embedding": str(embedding),  # pgvector accepts string format
            },
        )

    db.commit()
    logger.info("Stored chunks", document_id=document_id, count=len(chunks))


@app.task(bind=True, name="tasks.ingest.ingest_document")
def ingest_document(self, document_id: str) -> dict:
    """Main ingestion pipeline for a document.

    Pipeline:
    1. Download from storage → pending
    2. Extract text → extracting
    3. OCR if needed → ocr
    4. Canonicalize → canonicalizing
    5. Chunk → chunking
    6. Embed + generate tsvector → embedding
    7. Store chunks → ready
    8. On error → failed

    Args:
        document_id: UUID of the document to process

    Returns:
        Dict with processing result
    """
    logger.info("Starting document ingestion", document_id=document_id)

    db = get_db_session()
    storage = get_storage_backend()

    try:
        # Get document record
        result = db.execute(
            text("SELECT * FROM documents WHERE id = :id"),
            {"id": document_id},
        )
        doc = result.mappings().one_or_none()

        if not doc:
            raise ValueError(f"Document {document_id} not found")

        storage_key = doc["storage_key"]
        mime_type = doc["mime_type"]
        file_size = doc["file_size"]

        # 1. Download from storage backend
        update_document_status(db, document_id, "extracting")

        # Create temp file and write content from storage
        import asyncio
        file_content = asyncio.run(storage.download(storage_key))

        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name

        try:
            # 2. Extract text
            extractor_task = get_extractor(mime_type)
            extract_result = app.send_task(
                extractor_task,
                args=[tmp_path],
            ).get()

            text = extract_result["text"]
            page_count = extract_result["page_count"]
            page_texts = extract_result["page_texts"]

            # 3. Check if OCR needed
            is_ocr = False
            if check_ocr_needed(text, file_size, page_count):
                update_document_status(db, document_id, "ocr")
                logger.info("Running OCR fallback", document_id=document_id)

                ocr_result = app.send_task(
                    "tasks.ocr.ocr_document",
                    args=[tmp_path],
                ).get()

                text = ocr_result["text"]
                page_count = ocr_result["page_count"]
                page_texts = ocr_result["page_texts"]
                is_ocr = True

            # 4. Canonicalize
            update_document_status(db, document_id, "canonicalizing")

            canonical_result = app.send_task(
                "tasks.canonicalize.canonicalize_document",
                args=[page_texts, is_ocr],
            ).get()

            text = canonical_result["text"]
            page_texts = canonical_result["page_texts"]

            # 5 & 6. Chunk and embed
            update_document_status(db, document_id, "chunking")

            embed_result = app.send_task(
                "tasks.embed.chunk_and_embed",
                args=[text, page_texts, is_ocr],
            ).get()

            chunks = embed_result["chunks"]
            embedding_model = embed_result["model"]
            embedding_dim = embed_result["dimension"]

            # 7. Store chunks
            update_document_status(db, document_id, "embedding")
            store_chunks(db, document_id, chunks)

            # Update document as ready
            update_document_status(
                db,
                document_id,
                "ready",
                page_count=page_count,
                is_ocr=is_ocr,
                embedding_model=embedding_model,
                embedding_dim=embedding_dim,
            )

            logger.info(
                "Document ingestion complete",
                document_id=document_id,
                page_count=page_count,
                chunk_count=len(chunks),
                is_ocr=is_ocr,
            )

            return {
                "status": "ready",
                "document_id": document_id,
                "page_count": page_count,
                "chunk_count": len(chunks),
                "is_ocr": is_ocr,
            }

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        logger.error(
            "Document ingestion failed",
            document_id=document_id,
            error=str(e),
        )
        update_document_status(db, document_id, "failed", error=str(e))
        raise

    finally:
        db.close()
