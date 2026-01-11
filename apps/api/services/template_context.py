"""Context preparation helpers for template rendering.

Fetches case, client, and document data from the database
and formats it into template variables for rendering.
"""

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Case, Client, Document

logger = structlog.get_logger()


async def prepare_case_context(
    case_id: UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Prepare template context from case data.

    Fetches case with related client and documents, then formats
    into a dictionary suitable for template rendering.

    Args:
        case_id: Case identifier
        db: Database session

    Returns:
        Dictionary with case context variables:
        - client_name, client_code, client_email, client_phone
        - tax_year, case_type, case_status
        - documents: list of {filename, type, page_count}
        - document_count: total number of ready documents

    Raises:
        ValueError: If case not found

    Example:
        context = await prepare_case_context(case_id, db)
        # context = {
        #     "client_name": "John Doe",
        #     "tax_year": "2024",
        #     "documents": [{"filename": "w2.pdf", ...}],
        #     ...
        # }
    """
    # Fetch case with client (join for efficiency)
    result = await db.execute(
        select(Case, Client)
        .join(Client, Case.client_id == Client.id)
        .where(Case.id == case_id)
    )
    row = result.first()

    if not row:
        logger.error("Case not found", case_id=str(case_id))
        raise ValueError(f"Case not found: {case_id}")

    case, client = row

    # Fetch documents for case (only ready documents)
    docs_result = await db.execute(
        select(Document)
        .where(Document.case_id == case_id)
        .where(Document.processing_status == "ready")
        .order_by(Document.uploaded_at.desc())
    )
    documents = docs_result.scalars().all()

    # Build context dictionary
    context = {
        # Client information
        "client_name": client.name,
        "client_code": client.client_code,
        "client_email": client.email or "",
        "client_phone": client.phone or "",
        # Case information
        "tax_year": str(case.tax_year),
        "case_type": case.case_type,
        "case_status": case.status,
        # Documents
        "documents": [
            {
                "filename": doc.filename,
                "type": doc.tags[0] if doc.tags else "unknown",
                "page_count": doc.page_count or 0,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else "",
            }
            for doc in documents
        ],
        "document_count": len(documents),
    }

    logger.info(
        "Prepared case context",
        case_id=str(case_id),
        client_code=client.client_code,
        document_count=len(documents),
    )

    return context


async def prepare_client_context(
    client_id: UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Prepare template context from client data.

    Simpler alternative to prepare_case_context for templates
    that only need client information without case details.

    Args:
        client_id: Client identifier
        db: Database session

    Returns:
        Dictionary with client context variables

    Raises:
        ValueError: If client not found
    """
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()

    if not client:
        logger.error("Client not found", client_id=str(client_id))
        raise ValueError(f"Client not found: {client_id}")

    context = {
        "client_name": client.name,
        "client_code": client.client_code,
        "client_email": client.email or "",
        "client_phone": client.phone or "",
    }

    logger.info(
        "Prepared client context",
        client_id=str(client_id),
        client_code=client.client_code,
    )

    return context
