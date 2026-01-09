"""Cases router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Artifact, Case, Client, Document
from database.session import get_async_db
from shared.models.case import (
    Case as CaseSchema,
    CaseCreate,
    CaseSummary,
    CaseUpdate,
)

router = APIRouter()


@router.get("", response_model=list[CaseSummary])
async def list_cases(
    client_code: str | None = None,
    tax_year: int | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
) -> list[CaseSummary]:
    """List cases with optional filters."""
    query = (
        select(
            Case,
            Client.client_code,
            Client.name.label("client_name"),
            func.count(Document.id.distinct()).label("document_count"),
            func.count(Artifact.id.distinct()).label("artifact_count"),
        )
        .join(Client, Case.client_id == Client.id)
        .outerjoin(Document, Case.id == Document.case_id)
        .outerjoin(Artifact, Case.id == Artifact.case_id)
        .group_by(Case.id, Client.client_code, Client.name)
        .order_by(Case.updated_at.desc())
    )

    if client_code:
        query = query.where(Client.client_code == client_code)
    if tax_year:
        query = query.where(Case.tax_year == tax_year)
    if status:
        query = query.where(Case.status == status)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    return [
        CaseSummary(
            id=row.Case.id,
            client_code=row.client_code,
            client_name=row.client_name,
            tax_year=row.Case.tax_year,
            case_type=row.Case.case_type,
            status=row.Case.status,
            document_count=row.document_count,
            artifact_count=row.artifact_count,
            updated_at=row.Case.updated_at,
        )
        for row in rows
    ]


@router.get("/{case_id}", response_model=CaseSchema)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> CaseSchema:
    """Get a case by ID with related documents."""
    result = await db.execute(
        select(Case, Client.client_code, Client.name.label("client_name"))
        .join(Client, Case.client_id == Client.id)
        .where(Case.id == case_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    # Get counts
    doc_count = await db.execute(
        select(func.count()).select_from(Document).where(Document.case_id == case_id)
    )
    artifact_count = await db.execute(
        select(func.count()).select_from(Artifact).where(Artifact.case_id == case_id)
    )

    return CaseSchema(
        id=row.Case.id,
        client_id=row.Case.client_id,
        client_code=row.client_code,
        client_name=row.client_name,
        tax_year=row.Case.tax_year,
        case_type=row.Case.case_type,
        status=row.Case.status,
        notes=row.Case.notes,
        document_count=doc_count.scalar() or 0,
        artifact_count=artifact_count.scalar() or 0,
        created_at=row.Case.created_at,
        updated_at=row.Case.updated_at,
    )


@router.post("", response_model=CaseSchema, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    db: AsyncSession = Depends(get_async_db),
) -> CaseSchema:
    """Create a new case."""
    # Find or create client
    result = await db.execute(
        select(Client).where(Client.client_code == case_data.client_code)
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with code {case_data.client_code} not found",
        )

    # Check for existing case
    existing = await db.execute(
        select(Case).where(
            Case.client_id == client.id,
            Case.tax_year == case_data.tax_year,
            Case.case_type == case_data.case_type,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Case already exists for {case_data.client_code} {case_data.tax_year}",
        )

    case = Case(
        client_id=client.id,
        tax_year=case_data.tax_year,
        case_type=case_data.case_type,
        notes=case_data.notes,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)

    return CaseSchema(
        id=case.id,
        client_id=case.client_id,
        client_code=client.client_code,
        client_name=client.name,
        tax_year=case.tax_year,
        case_type=case.case_type,
        status=case.status,
        notes=case.notes,
        document_count=0,
        artifact_count=0,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.patch("/{case_id}", response_model=CaseSchema)
async def update_case(
    case_id: UUID,
    case_data: CaseUpdate,
    db: AsyncSession = Depends(get_async_db),
) -> CaseSchema:
    """Update a case."""
    result = await db.execute(
        select(Case, Client.client_code, Client.name.label("client_name"))
        .join(Client, Case.client_id == Client.id)
        .where(Case.id == case_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    case = row.Case
    update_data = case_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(case, field, value)

    await db.commit()
    await db.refresh(case)

    # Get counts
    doc_count = await db.execute(
        select(func.count()).select_from(Document).where(Document.case_id == case_id)
    )
    artifact_count = await db.execute(
        select(func.count()).select_from(Artifact).where(Artifact.case_id == case_id)
    )

    return CaseSchema(
        id=case.id,
        client_id=case.client_id,
        client_code=row.client_code,
        client_name=row.client_name,
        tax_year=case.tax_year,
        case_type=case.case_type,
        status=case.status,
        notes=case.notes,
        document_count=doc_count.scalar() or 0,
        artifact_count=artifact_count.scalar() or 0,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )
