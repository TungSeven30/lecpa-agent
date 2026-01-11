"""Field extraction tasks for structured data extraction from tax documents.

This module provides background tasks for extracting structured fields from
tax documents (W-2, 1099, K-1) using the ExtractionAgent. It can be triggered
manually via API or automatically during document ingestion for tagged documents.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Add packages to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "apps" / "api"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "packages"))

from main import app

logger = structlog.get_logger()


def get_db_session() -> Session:
    """Get a synchronous database session for worker tasks.

    Returns:
        SQLAlchemy session

    Raises:
        ValueError: If DATABASE_URL not configured
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not set")
    engine = create_engine(database_url)
    return Session(engine)


def should_auto_extract(tags: list[str] | None) -> bool:
    """Check if document should be auto-extracted based on tags.

    Auto-extraction triggers for documents tagged as tax forms.

    Args:
        tags: Document tags list

    Returns:
        True if document should be auto-extracted
    """
    if not tags:
        return False

    auto_extract_tags = {"W2", "W-2", "1099", "K1", "K-1"}
    return bool(set(tags) & auto_extract_tags)


def detect_document_type(tags: list[str] | None, filename: str | None = None) -> str | None:
    """Detect document type from tags or filename.

    Args:
        tags: Document tags
        filename: Original filename

    Returns:
        Document type string or None
    """
    if tags:
        tag_set = {t.upper().replace("-", "") for t in tags}
        if "W2" in tag_set:
            return "W2"
        if any("1099" in t for t in tag_set):
            return "1099"
        if "K1" in tag_set:
            return "K1"

    if filename:
        filename_upper = filename.upper()
        if "W2" in filename_upper or "W-2" in filename_upper:
            return "W2"
        if "1099" in filename_upper:
            return "1099"
        if "K1" in filename_upper or "K-1" in filename_upper:
            return "K1"

    return None


@app.task(bind=True, name="tasks.field_extraction.extract_document_fields")
def extract_document_fields(
    _self,  # noqa: ARG001 - Celery bound task requires self
    document_id: str,
    document_type: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Extract structured fields from a tax document.

    Uses ExtractionAgent to parse W-2, 1099, or K-1 documents
    and store the extracted data as an artifact.

    Args:
        document_id: UUID of the document to process
        document_type: Optional type hint (W2, 1099, K1)
        force: If True, re-extract even if artifact exists

    Returns:
        Dict with extraction result and artifact_id
    """
    logger.info(
        "Starting field extraction",
        document_id=document_id,
        document_type=document_type,
        force=force,
    )

    db = get_db_session()

    try:
        # Get document record
        result = db.execute(
            text("""
                SELECT id, case_id, filename, tags, processing_status
                FROM documents WHERE id = :id
            """),
            {"id": document_id},
        )
        doc = result.mappings().one_or_none()

        if not doc:
            raise ValueError(f"Document {document_id} not found")

        # Check if document is ready for extraction
        if doc["processing_status"] != "ready":
            logger.warning(
                "Document not ready for field extraction",
                document_id=document_id,
                status=doc["processing_status"],
            )
            return {
                "status": "skipped",
                "reason": f"Document status is {doc['processing_status']}, expected 'ready'",
            }

        # Check for existing extraction artifact (unless force=True)
        if not force:
            existing = db.execute(
                text("""
                    SELECT id FROM artifacts
                    WHERE document_id = :doc_id AND artifact_type = 'extraction_result'
                    LIMIT 1
                """),
                {"doc_id": document_id},
            )
            if existing.one_or_none():
                logger.info(
                    "Extraction artifact already exists",
                    document_id=document_id,
                )
                return {
                    "status": "skipped",
                    "reason": "Extraction already exists (use force=True to re-extract)",
                }

        # Detect document type if not provided
        tags = doc["tags"] or []
        detected_type = document_type or detect_document_type(tags, doc["filename"])

        if not detected_type:
            logger.info(
                "Could not determine document type for extraction",
                document_id=document_id,
                tags=tags,
            )
            return {
                "status": "skipped",
                "reason": "Unable to determine document type (W2, 1099, K1)",
            }

        # Run async extraction
        result = asyncio.run(
            _run_extraction(
                document_id=document_id,
                case_id=doc["case_id"],
                document_type=detected_type,
            )
        )

        logger.info(
            "Field extraction complete",
            document_id=document_id,
            document_type=detected_type,
            artifact_id=result.get("artifact_id"),
            confidence=result.get("confidence"),
        )

        return {
            "status": "success",
            "document_id": document_id,
            "document_type": detected_type,
            "artifact_id": result.get("artifact_id"),
            "confidence": result.get("confidence"),
            "needs_review": result.get("needs_review", False),
            "anomalies_count": result.get("anomalies_count", 0),
        }

    except Exception as e:
        logger.error(
            "Field extraction failed",
            document_id=document_id,
            error=str(e),
        )
        raise

    finally:
        db.close()


async def _run_extraction(
    document_id: str,
    _case_id: str | None,
    document_type: str,
) -> dict[str, Any]:
    """Run async extraction using ExtractionAgent.

    Args:
        document_id: Document UUID
        _case_id: Case UUID (reserved for artifact association)
        document_type: Type of document (W2, 1099, K1)

    Returns:
        Extraction result dict
    """
    # Import here to avoid circular imports and ensure proper async context
    from services.agents.extraction_agent import ExtractionAgent
    from services.model_router import ModelRouter
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    database_url = os.environ.get("DATABASE_URL", "")
    # Convert sync URL to async
    if database_url.startswith("postgresql://"):
        async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    else:
        async_url = database_url

    engine = create_async_engine(async_url)

    async with AsyncSession(engine) as db:
        model_router = ModelRouter()
        extraction_agent = ExtractionAgent(model_router)

        result = await extraction_agent.extract_document(
            document_id=UUID(document_id),
            db=db,
            document_type=document_type,
        )

        return {
            "artifact_id": str(result.artifact_id) if result.artifact_id else None,
            "confidence": result.confidence.value if result.confidence else None,
            "needs_review": result.needs_review,
            "anomalies_count": len(result.anomalies) if result.anomalies else 0,
        }


@app.task(bind=True, name="tasks.field_extraction.batch_extract")
def batch_extract(
    _self,  # noqa: ARG001 - Celery bound task requires self
    document_ids: list[str],
    document_type: str | None = None,
) -> dict[str, Any]:
    """Batch extract fields from multiple documents.

    Useful for processing multiple documents of the same type.

    Args:
        document_ids: List of document UUIDs
        document_type: Optional type hint for all documents

    Returns:
        Summary of extraction results
    """
    logger.info(
        "Starting batch field extraction",
        count=len(document_ids),
        document_type=document_type,
    )

    results = {
        "total": len(document_ids),
        "success": 0,
        "skipped": 0,
        "failed": 0,
        "details": [],
    }

    for doc_id in document_ids:
        try:
            result = extract_document_fields.delay(
                doc_id,
                document_type=document_type,
            ).get(timeout=300)  # 5 min timeout per document

            if result["status"] == "success":
                results["success"] += 1
            else:
                results["skipped"] += 1

            results["details"].append({
                "document_id": doc_id,
                **result,
            })

        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "document_id": doc_id,
                "status": "failed",
                "error": str(e),
            })

    logger.info(
        "Batch field extraction complete",
        total=results["total"],
        success=results["success"],
        skipped=results["skipped"],
        failed=results["failed"],
    )

    return results


@app.task(bind=True, name="tasks.field_extraction.auto_extract_if_eligible")
def auto_extract_if_eligible(_self, document_id: str) -> dict[str, Any]:  # noqa: ARG001
    """Check if document should be auto-extracted and trigger if eligible.

    Called from the ingestion pipeline after document is ready.
    Only extracts if document has appropriate tags (W2, 1099, K1).

    Args:
        document_id: Document UUID

    Returns:
        Result dict indicating whether extraction was triggered
    """
    # Check if auto-extraction is enabled
    auto_extract_enabled = os.environ.get("AUTO_EXTRACT_ENABLED", "false").lower() == "true"

    if not auto_extract_enabled:
        return {
            "status": "skipped",
            "reason": "Auto-extraction is disabled (set AUTO_EXTRACT_ENABLED=true)",
        }

    db = get_db_session()

    try:
        result = db.execute(
            text("SELECT tags, filename FROM documents WHERE id = :id"),
            {"id": document_id},
        )
        doc = result.mappings().one_or_none()

        if not doc:
            return {"status": "skipped", "reason": "Document not found"}

        tags = doc["tags"] or []
        filename = doc["filename"]

        if not should_auto_extract(tags):
            return {
                "status": "skipped",
                "reason": f"Document tags {tags} do not match auto-extract criteria",
            }

        # Trigger extraction
        logger.info(
            "Auto-triggering field extraction",
            document_id=document_id,
            tags=tags,
        )

        extract_document_fields.delay(document_id)

        return {
            "status": "triggered",
            "document_id": document_id,
            "detected_type": detect_document_type(tags, filename),
        }

    finally:
        db.close()
