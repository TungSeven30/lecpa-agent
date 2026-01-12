"""Ingest router for NAS sync agent communication.

Handles notifications from the NAS sync agent about file changes
and manages the approval queue for new clients/cases.
"""

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from celery import Celery
from database.models import (
    Case,
    Client,
    ClientRelationship,
    Document,
    SyncQueueItem,
)
from database.session import get_async_db
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Celery client for triggering ingestion tasks
celery_app = Celery(broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"))

router = APIRouter()

# Configuration
AUTO_APPROVE_HOURS = int(os.environ.get("AUTO_APPROVE_HOURS", "4"))
SOFT_DELETE_RETENTION_DAYS = int(os.environ.get("SOFT_DELETE_RETENTION_DAYS", "90"))


# =============================================================================
# Request/Response Models
# =============================================================================


class ParsedInfo(BaseModel):
    """Parsed path information from sync agent."""

    client_code: str | None = None
    client_name: str | None = None
    client_type: str | None = None
    year: int | None = None
    folder_tag: str | None = None
    is_permanent: bool = False
    relative_path: str = ""
    detected_tags: list[str] = Field(default_factory=list)


class FileArrivedRequest(BaseModel):
    """Request body for file arrival notification."""

    nas_path: str
    file_size: int
    file_hash: str
    modified_time: datetime
    parsed_info: ParsedInfo


class FileArrivedResponse(BaseModel):
    """Response for file arrival notification."""

    status: str  # queued, pending_approval, duplicate, error
    document_id: str | None = None
    queue_item_id: str | None = None
    existing_document_id: str | None = None
    message: str


class FileDeletedRequest(BaseModel):
    """Request body for file deletion notification."""

    nas_path: str


class FileDeletedResponse(BaseModel):
    """Response for file deletion notification."""

    status: str  # soft_deleted, not_found, error
    document_id: str | None = None
    retention_until: datetime | None = None
    message: str


class RelationshipRequest(BaseModel):
    """Request body for client relationship notification."""

    individual_code: str
    business_code: str
    source: str  # lnk_shortcut, manual
    source_path: str | None = None


class SyncQueueItemResponse(BaseModel):
    """Response model for sync queue items."""

    id: str
    item_type: str
    nas_path: str
    parsed_data: dict[str, Any]
    status: str
    created_at: datetime
    auto_approve_at: datetime | None = None
    reviewed_at: datetime | None = None


class SyncQueueListResponse(BaseModel):
    """Response model for sync queue list."""

    items: list[SyncQueueItemResponse]
    total: int
    pending_count: int


class QueueActionRequest(BaseModel):
    """Request body for queue approve/reject."""

    notes: str | None = None


class SyncStatusResponse(BaseModel):
    """Response model for sync status."""

    agent_status: str
    last_heartbeat: datetime | None = None
    last_file_event: datetime | None = None
    queue_stats: dict[str, int]
    today_stats: dict[str, int]


class InitialScanRequest(BaseModel):
    """Request body for initial scan trigger."""

    client_filter: list[str] | None = None
    year_filter: list[int] | None = None
    dry_run: bool = False


class ScanStatusResponse(BaseModel):
    """Response model for scan status."""

    status: str
    scan_id: str | None = None
    estimated_files: int | None = None
    files_scanned: int = 0
    files_queued: int = 0
    files_skipped: int = 0
    errors: list[str] = Field(default_factory=list)


# =============================================================================
# State tracking (in-memory for simplicity)
# =============================================================================

_last_heartbeat: datetime | None = None
_last_file_event: datetime | None = None


# =============================================================================
# File Event Endpoints
# =============================================================================


@router.post("/file-arrived", response_model=FileArrivedResponse)
async def file_arrived(
    request: FileArrivedRequest,
    db: AsyncSession = Depends(get_async_db),
) -> FileArrivedResponse:
    """Handle file arrival notification from NAS sync agent.

    This endpoint is called when the sync agent detects a new or modified file.
    The flow:
    1. Check if file already exists (by nas_full_path or file_hash)
    2. Check if client exists → if not, queue for approval
    3. Check if case exists → if not, queue for approval
    4. Create document record and queue for ingestion
    """
    global _last_file_event
    _last_file_event = datetime.now(UTC)

    parsed = request.parsed_info

    if not parsed.client_code:
        return FileArrivedResponse(
            status="error",
            message="No client code in parsed path",
        )

    # Check for duplicate by NAS path
    result = await db.execute(
        select(Document).where(Document.nas_full_path == request.nas_path)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update last_seen_at for existing document
        existing.last_seen_at = datetime.now(UTC)
        await db.commit()
        return FileArrivedResponse(
            status="duplicate",
            existing_document_id=str(existing.id),
            message="File already indexed",
        )

    # Check for duplicate by hash (same content, different path)
    if request.file_hash:
        result = await db.execute(
            select(Document).where(Document.file_hash == request.file_hash)
        )
        hash_match = result.scalar_one_or_none()
        if hash_match:
            return FileArrivedResponse(
                status="duplicate",
                existing_document_id=str(hash_match.id),
                message="File with same content already indexed",
            )

    # Find or create client
    client = await _get_or_queue_client(
        db=db,
        client_code=parsed.client_code,
        client_name=parsed.client_name,
        client_type=parsed.client_type,
        nas_path=request.nas_path,
    )

    if client is None:
        # Client queued for approval
        result = await db.execute(
            select(SyncQueueItem).where(
                SyncQueueItem.nas_path.like(f"%{parsed.client_code}_%"),
                SyncQueueItem.item_type == "client",
            )
        )
        queue_item = result.scalars().first()
        return FileArrivedResponse(
            status="pending_approval",
            queue_item_id=str(queue_item.id) if queue_item else None,
            message="Client requires approval before ingestion",
        )

    # Find or create case
    case = await _get_or_queue_case(
        db=db,
        client=client,
        year=parsed.year,
        is_permanent=parsed.is_permanent,
        nas_path=request.nas_path,
    )

    if case is None:
        # Case queued for approval
        return FileArrivedResponse(
            status="pending_approval",
            message="Case requires approval before ingestion",
        )

    # Create document record
    doc_id = uuid.uuid4()
    document = Document(
        id=doc_id,
        case_id=case.id,
        filename=request.nas_path.split("/")[-1],
        original_filename=request.nas_path.split("/")[-1],
        storage_key=request.nas_path,  # For NAS, storage_key is the full path
        mime_type=_guess_mime_type(request.nas_path),
        file_size=request.file_size,
        nas_relative_path=parsed.relative_path,
        nas_full_path=request.nas_path,
        is_permanent=parsed.is_permanent,
        folder_tag=parsed.folder_tag,
        file_hash=request.file_hash.replace("sha256:", "")
        if request.file_hash
        else None,
        tags=parsed.detected_tags,
        processing_status="pending",
        last_seen_at=datetime.now(UTC),
    )
    db.add(document)
    await db.commit()

    # Queue ingestion task
    celery_app.send_task("tasks.ingest.ingest_document", args=[str(document.id)])

    return FileArrivedResponse(
        status="queued",
        document_id=str(document.id),
        message="Document queued for ingestion",
    )


@router.post("/file-deleted", response_model=FileDeletedResponse)
async def file_deleted(
    request: FileDeletedRequest,
    db: AsyncSession = Depends(get_async_db),
) -> FileDeletedResponse:
    """Handle file deletion notification from NAS sync agent.

    Performs a soft delete by setting deleted_at timestamp.
    Files are retained for SOFT_DELETE_RETENTION_DAYS before permanent deletion.
    """
    global _last_file_event
    _last_file_event = datetime.now(UTC)

    result = await db.execute(
        select(Document).where(Document.nas_full_path == request.nas_path)
    )
    document = result.scalar_one_or_none()

    if not document:
        return FileDeletedResponse(
            status="not_found",
            message="Document not found in database",
        )

    # Soft delete
    now = datetime.now(UTC)
    retention_until = now + timedelta(days=SOFT_DELETE_RETENTION_DAYS)
    document.deleted_at = now
    await db.commit()

    return FileDeletedResponse(
        status="soft_deleted",
        document_id=str(document.id),
        retention_until=retention_until,
        message=f"Document soft-deleted, will be purged after {retention_until.date()}",
    )


@router.post("/heartbeat")
async def heartbeat() -> dict:
    """Receive heartbeat from sync agent."""
    global _last_heartbeat
    _last_heartbeat = datetime.now(UTC)
    return {"status": "ok", "received_at": _last_heartbeat.isoformat()}


# =============================================================================
# Sync Queue Management Endpoints
# =============================================================================


@router.get("/sync-queue", response_model=SyncQueueListResponse)
async def list_sync_queue(
    status_filter: str = Query(None, alias="status"),
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_async_db),
) -> SyncQueueListResponse:
    """List sync queue items for admin review."""
    query = select(SyncQueueItem).order_by(SyncQueueItem.created_at.desc())

    if status_filter:
        query = query.where(SyncQueueItem.status == status_filter)

    # Get total counts
    total_query = select(func.count(SyncQueueItem.id))
    pending_query = select(func.count(SyncQueueItem.id)).where(
        SyncQueueItem.status == "pending"
    )

    if status_filter:
        total_query = total_query.where(SyncQueueItem.status == status_filter)

    total_result = await db.execute(total_query)
    pending_result = await db.execute(pending_query)

    total = total_result.scalar() or 0
    pending_count = pending_result.scalar() or 0

    # Get items
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return SyncQueueListResponse(
        items=[
            SyncQueueItemResponse(
                id=str(item.id),
                item_type=item.item_type,
                nas_path=item.nas_path,
                parsed_data=item.parsed_data,
                status=item.status,
                created_at=item.created_at,
                auto_approve_at=item.auto_approve_at,
                reviewed_at=item.reviewed_at,
            )
            for item in items
        ],
        total=total,
        pending_count=pending_count,
    )


@router.post("/sync-queue/{item_id}/approve")
async def approve_queue_item(
    item_id: UUID,
    request: QueueActionRequest | None = None,
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """Approve a sync queue item (client or case)."""
    result = await db.execute(select(SyncQueueItem).where(SyncQueueItem.id == item_id))
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue item not found",
        )

    if item.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Item already {item.status}",
        )

    # Create the client or case
    if item.item_type == "client":
        await _create_client_from_queue(db, item)
    elif item.item_type == "case":
        await _create_case_from_queue(db, item)

    # Update queue item
    item.status = "approved"
    item.reviewed_at = datetime.now(UTC)
    if request and request.notes:
        item.notes = request.notes

    await db.commit()

    return {"status": "approved", "item_id": str(item_id)}


@router.post("/sync-queue/{item_id}/reject")
async def reject_queue_item(
    item_id: UUID,
    request: QueueActionRequest | None = None,
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """Reject a sync queue item."""
    result = await db.execute(select(SyncQueueItem).where(SyncQueueItem.id == item_id))
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue item not found",
        )

    if item.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Item already {item.status}",
        )

    item.status = "rejected"
    item.reviewed_at = datetime.now(UTC)
    if request and request.notes:
        item.notes = request.notes

    await db.commit()

    return {"status": "rejected", "item_id": str(item_id)}


# =============================================================================
# Relationship Endpoint
# =============================================================================


@router.post("/relationship")
async def create_relationship(
    request: RelationshipRequest,
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """Record a client relationship discovered from .lnk shortcut."""
    # Find individual client
    result = await db.execute(
        select(Client).where(Client.client_code == request.individual_code)
    )
    individual = result.scalar_one_or_none()

    if not individual:
        return {"status": "skipped", "message": "Individual client not found"}

    # Find business client
    result = await db.execute(
        select(Client).where(Client.client_code == request.business_code)
    )
    business = result.scalar_one_or_none()

    if not business:
        return {"status": "skipped", "message": "Business client not found"}

    # Check if relationship already exists
    result = await db.execute(
        select(ClientRelationship).where(
            ClientRelationship.individual_id == individual.id,
            ClientRelationship.business_id == business.id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        return {"status": "exists", "relationship_id": str(existing.id)}

    # Create relationship
    relationship = ClientRelationship(
        individual_id=individual.id,
        business_id=business.id,
        source=request.source,
        source_path=request.source_path,
    )
    db.add(relationship)
    await db.commit()

    return {"status": "created", "relationship_id": str(relationship.id)}


# =============================================================================
# Status Endpoint
# =============================================================================


@router.get("/sync-status", response_model=SyncStatusResponse)
async def get_sync_status(
    db: AsyncSession = Depends(get_async_db),
) -> SyncStatusResponse:
    """Get current sync status for monitoring and digest."""
    # Calculate agent status based on last heartbeat
    if _last_heartbeat is None:
        agent_status = "disconnected"
    elif datetime.now(UTC) - _last_heartbeat > timedelta(minutes=5):
        agent_status = "stale"
    else:
        agent_status = "healthy"

    # Get queue stats
    pending_result = await db.execute(
        select(func.count(SyncQueueItem.id)).where(SyncQueueItem.status == "pending")
    )
    pending_approval = pending_result.scalar() or 0

    processing_result = await db.execute(
        select(func.count(Document.id)).where(
            Document.processing_status.in_(["pending", "extracting", "chunking"])
        )
    )
    processing = processing_result.scalar() or 0

    # Get today's stats
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    detected_result = await db.execute(
        select(func.count(Document.id)).where(Document.created_at >= today_start)
    )
    files_detected = detected_result.scalar() or 0

    processed_result = await db.execute(
        select(func.count(Document.id)).where(
            Document.created_at >= today_start,
            Document.processing_status == "ready",
        )
    )
    files_processed = processed_result.scalar() or 0

    failed_result = await db.execute(
        select(func.count(Document.id)).where(
            Document.created_at >= today_start,
            Document.processing_status == "failed",
        )
    )
    files_failed = failed_result.scalar() or 0

    return SyncStatusResponse(
        agent_status=agent_status,
        last_heartbeat=_last_heartbeat,
        last_file_event=_last_file_event,
        queue_stats={
            "pending_approval": pending_approval,
            "processing": processing,
            "failed_today": files_failed,
        },
        today_stats={
            "files_detected": files_detected,
            "files_processed": files_processed,
            "files_failed": files_failed,
        },
    )


# =============================================================================
# Helper Functions
# =============================================================================


async def _get_or_queue_client(
    db: AsyncSession,
    client_code: str,
    client_name: str | None,
    client_type: str | None,
    nas_path: str,
) -> Client | None:
    """Get existing client or queue for approval if new.

    Returns:
        Client if exists and approved, None if queued for approval
    """
    result = await db.execute(select(Client).where(Client.client_code == client_code))
    client = result.scalar_one_or_none()

    if client:
        if client.approval_status == "approved":
            return client
        return None  # Client exists but not approved

    # Queue new client for approval
    queue_item = SyncQueueItem(
        item_type="client",
        nas_path=nas_path.rsplit("/", 2)[0] + "/",  # Client folder path
        parsed_data={
            "client_code": client_code,
            "client_name": client_name,
            "client_type": client_type or "individual",
        },
        status="pending",
        auto_approve_at=datetime.now(UTC) + timedelta(hours=AUTO_APPROVE_HOURS),
    )
    db.add(queue_item)
    await db.commit()

    return None


async def _get_or_queue_case(
    db: AsyncSession,
    client: Client,
    year: int | None,
    is_permanent: bool,
    nas_path: str,
) -> Case | None:
    """Get existing case or queue for approval if new.

    For permanent folders, creates/gets a special "Permanent" case.

    Returns:
        Case if exists, None if queued for approval
    """
    if is_permanent:
        # Look for or create permanent case (year = 0 or some sentinel)
        result = await db.execute(
            select(Case).where(
                Case.client_id == client.id,
                Case.is_permanent.is_(True),
            )
        )
        case = result.scalar_one_or_none()

        if not case:
            # Auto-create permanent case (no approval needed)
            case = Case(
                client_id=client.id,
                tax_year=0,  # Sentinel for permanent
                case_type="other",
                status="intake",
                is_permanent=True,
                nas_year_path=nas_path.rsplit("/", 1)[0],
            )
            db.add(case)
            await db.commit()
            await db.refresh(case)

        return case

    if year is None:
        # No year and not permanent - might be a special folder
        # Create a generic case for this year
        year = datetime.now().year

    # Look for existing case
    result = await db.execute(
        select(Case).where(
            Case.client_id == client.id,
            Case.tax_year == year,
        )
    )
    case = result.scalar_one_or_none()

    if case:
        return case

    # Queue new case for approval
    queue_item = SyncQueueItem(
        item_type="case",
        nas_path=nas_path.rsplit("/", 1)[0] + "/",  # Year folder path
        parsed_data={
            "client_id": str(client.id),
            "client_code": client.client_code,
            "year": year,
        },
        status="pending",
        auto_approve_at=datetime.now(UTC) + timedelta(hours=AUTO_APPROVE_HOURS),
    )
    db.add(queue_item)
    await db.commit()

    return None


async def _create_client_from_queue(db: AsyncSession, item: SyncQueueItem) -> Client:
    """Create a client from an approved queue item."""
    data = item.parsed_data
    client = Client(
        client_code=data["client_code"],
        name=data.get("client_name", data["client_code"]),
        client_type=data.get("client_type", "individual"),
        nas_folder_path=item.nas_path,
        approval_status="approved",
        approved_at=datetime.now(UTC),
    )
    db.add(client)
    await db.commit()
    return client


async def _create_case_from_queue(db: AsyncSession, item: SyncQueueItem) -> Case:
    """Create a case from an approved queue item."""
    data = item.parsed_data
    case = Case(
        client_id=UUID(data["client_id"]),
        tax_year=data["year"],
        case_type="tax_return",
        status="intake",
        nas_year_path=item.nas_path,
    )
    db.add(case)
    await db.commit()
    return case


def _guess_mime_type(path: str) -> str:
    """Guess MIME type from file extension."""
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    mime_types = {
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "txt": "text/plain",
    }
    return mime_types.get(ext, "application/octet-stream")
