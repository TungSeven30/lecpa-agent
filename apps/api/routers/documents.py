"""Documents router."""

import io
import os
import uuid
from uuid import UUID

from celery import Celery
from database.models import Case, Document
from database.session import get_async_db
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from services.storage import StorageBackend, get_storage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.document import Document as DocumentSchema
from shared.models.document import DocumentUpdate

# Celery client for triggering ingestion tasks
celery_app = Celery(broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"))

router = APIRouter()


@router.get("", response_model=list[DocumentSchema])
async def list_documents(
    case_id: UUID | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
) -> list[DocumentSchema]:
    """List documents with optional filters."""
    query = select(Document).order_by(Document.created_at.desc())

    if case_id:
        query = query.where(Document.case_id == case_id)
    if status:
        query = query.where(Document.processing_status == status)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    documents = result.scalars().all()

    return [DocumentSchema.model_validate(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentSchema)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> DocumentSchema:
    """Get a document by ID."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentSchema.model_validate(document)


@router.post("/upload", response_model=DocumentSchema, status_code=status.HTTP_201_CREATED)
async def upload_document(
    case_id: UUID,
    file: UploadFile = File(...),
    tags: list[str] | None = None,
    db: AsyncSession = Depends(get_async_db),
    storage: StorageBackend = Depends(get_storage),
) -> DocumentSchema:
    """Upload a document to a case.

    The document is stored using the configured storage backend (filesystem or S3).
    For NAS deployment, files are written directly to /volume1/LeCPA/ClientFiles.
    """
    # Verify case exists
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    # Generate unique filename and storage key
    doc_id = uuid.uuid4()
    original_filename = file.filename or "unknown"
    extension = original_filename.rsplit(".", 1)[-1] if "." in original_filename else ""
    filename = f"{doc_id}.{extension}" if extension else str(doc_id)

    # Storage key format: {client_code}/{tax_year}/{filename}
    # This matches NAS folder structure: ClientFiles/1001/2024/file.pdf
    storage_key = f"documents/{case_id}/{filename}"

    # Upload to storage backend
    # Reset file position before reading
    await file.seek(0)
    file_obj = io.BytesIO(await file.read())
    file_size = len(file_obj.getvalue())

    await storage.upload(file_obj, storage_key)

    # Create document record
    document = Document(
        id=doc_id,
        case_id=case_id,
        filename=filename,
        original_filename=original_filename,
        storage_key=storage_key,
        mime_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        tags=tags or [],
        processing_status="pending",
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Queue ingestion task
    celery_app.send_task("tasks.ingest.ingest_document", args=[str(document.id)])

    return DocumentSchema.model_validate(document)


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    storage: StorageBackend = Depends(get_storage),
) -> StreamingResponse:
    """Download a document.

    For filesystem storage, streams the file directly.
    For S3 storage, would return a presigned URL (future enhancement).
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Download file content from storage
    try:
        file_content = await storage.download(document.storage_key)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found in storage",
        )

    # Stream file to client
    return StreamingResponse(
        io.BytesIO(file_content),
        media_type=document.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{document.original_filename}"'
        },
    )


@router.patch("/{document_id}", response_model=DocumentSchema)
async def update_document(
    document_id: UUID,
    update_data: DocumentUpdate,
    db: AsyncSession = Depends(get_async_db),
) -> DocumentSchema:
    """Update document metadata/status."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(document, field, value)

    await db.commit()
    await db.refresh(document)

    return DocumentSchema.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    storage: StorageBackend = Depends(get_storage),
) -> None:
    """Delete a document from storage and database."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Delete from storage backend
    try:
        await storage.delete(document.storage_key)
    except Exception:
        # Log error but continue with database deletion
        # (file might already be deleted or inaccessible)
        pass

    # Delete from database (chunks cascade)
    await db.delete(document)
    await db.commit()
