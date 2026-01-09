"""Artifacts router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Artifact, Case
from database.session import get_async_db
from shared.models.artifact import (
    Artifact as ArtifactSchema,
    ArtifactCreate,
    ArtifactSummary,
    ArtifactUpdate,
)

router = APIRouter()


@router.get("", response_model=list[ArtifactSummary])
async def list_artifacts(
    case_id: UUID | None = None,
    artifact_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
) -> list[ArtifactSummary]:
    """List artifacts with optional filters."""
    query = select(Artifact).order_by(Artifact.updated_at.desc())

    if case_id:
        query = query.where(Artifact.case_id == case_id)
    if artifact_type:
        query = query.where(Artifact.artifact_type == artifact_type)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    artifacts = result.scalars().all()

    return [
        ArtifactSummary(
            id=a.id,
            case_id=a.case_id,
            artifact_type=a.artifact_type,
            title=a.title,
            version=a.version,
            is_draft=a.is_draft,
            updated_at=a.updated_at,
        )
        for a in artifacts
    ]


@router.get("/{artifact_id}", response_model=ArtifactSchema)
async def get_artifact(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> ArtifactSchema:
    """Get an artifact by ID."""
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )

    return ArtifactSchema.model_validate(artifact)


@router.post("", response_model=ArtifactSchema, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    artifact_data: ArtifactCreate,
    db: AsyncSession = Depends(get_async_db),
) -> ArtifactSchema:
    """Create a new artifact."""
    # Verify case exists
    result = await db.execute(select(Case).where(Case.id == artifact_data.case_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    artifact = Artifact(**artifact_data.model_dump())
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)

    return ArtifactSchema.model_validate(artifact)


@router.patch("/{artifact_id}", response_model=ArtifactSchema)
async def update_artifact(
    artifact_id: UUID,
    update_data: ArtifactUpdate,
    db: AsyncSession = Depends(get_async_db),
) -> ArtifactSchema:
    """Update an artifact."""
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )

    # Increment version on content update
    update_dict = update_data.model_dump(exclude_unset=True)
    if "content" in update_dict:
        artifact.version += 1

    for field, value in update_dict.items():
        setattr(artifact, field, value)

    await db.commit()
    await db.refresh(artifact)

    return ArtifactSchema.model_validate(artifact)


@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(
    artifact_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Delete an artifact."""
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found",
        )

    await db.delete(artifact)
    await db.commit()
