"""Documents router."""

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Case, Document
from database.session import get_async_db
from services.storage import StorageService, get_storage_service
from shared.models.document import Document as DocumentSchema
from shared.models.document import DocumentCreate, DocumentUpdate

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
    storage: StorageService = Depends(get_storage_service),
) -> DocumentSchema:
    """Upload a document to a case."""
    # Verify case exists
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Generate unique filename and S3 key
    doc_id = uuid.uuid4()
    original_filename = file.filename or "unknown"
    extension = original_filename.rsplit(".", 1)[-1] if "." in original_filename else ""
    filename = f"{doc_id}.{extension}" if extension else str(doc_id)
    s3_key = f"documents/{case_id}/{filename}"

    # Upload to S3
    await storage.upload_file(s3_key, content, file.content_type or "application/octet-stream")

    # Create document record
    document = Document(
        id=doc_id,
        case_id=case_id,
        filename=filename,
        original_filename=original_filename,
        s3_key=s3_key,
        mime_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        tags=tags or [],
        processing_status="pending",
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    # TODO: Queue ingestion task

    return DocumentSchema.model_validate(document)


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    storage: StorageService = Depends(get_storage_service),
) -> dict[str, str]:
    """Get a presigned URL to download a document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    url = await storage.get_presigned_url(document.s3_key)
    return {"url": url, "filename": document.original_filename}


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
    storage: StorageService = Depends(get_storage_service),
) -> None:
    """Delete a document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Delete from S3
    await storage.delete_file(document.s3_key)

    # Delete from database (chunks cascade)
    await db.delete(document)
    await db.commit()
