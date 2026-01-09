"""Clients router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Client
from database.session import get_async_db
from shared.models.case import Client as ClientSchema
from shared.models.case import ClientCreate

router = APIRouter()


@router.get("", response_model=list[ClientSchema])
async def list_clients(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
) -> list[ClientSchema]:
    """List all clients."""
    result = await db.execute(
        select(Client).order_by(Client.client_code).offset(skip).limit(limit)
    )
    clients = result.scalars().all()
    return [ClientSchema.model_validate(c) for c in clients]


@router.get("/{client_code}", response_model=ClientSchema)
async def get_client(
    client_code: str,
    db: AsyncSession = Depends(get_async_db),
) -> ClientSchema:
    """Get a client by client code."""
    result = await db.execute(
        select(Client).where(Client.client_code == client_code)
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client with code {client_code} not found",
        )

    return ClientSchema.model_validate(client)


@router.post("", response_model=ClientSchema, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: ClientCreate,
    db: AsyncSession = Depends(get_async_db),
) -> ClientSchema:
    """Create a new client."""
    # Check if client code already exists
    result = await db.execute(
        select(Client).where(Client.client_code == client_data.client_code)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Client with code {client_data.client_code} already exists",
        )

    client = Client(**client_data.model_dump())
    db.add(client)
    await db.commit()
    await db.refresh(client)

    return ClientSchema.model_validate(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> None:
    """Delete a client."""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    await db.delete(client)
    await db.commit()
