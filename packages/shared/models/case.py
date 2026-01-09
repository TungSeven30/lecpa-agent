"""Case and Client Pydantic models."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CaseType(str, Enum):
    """Type of tax case."""

    TAX_RETURN = "tax_return"
    NOTICE = "notice"
    CORRESPONDENCE = "correspondence"
    AMENDMENT = "amendment"
    EXTENSION = "extension"
    OTHER = "other"


class CaseStatus(str, Enum):
    """Case workflow status."""

    INTAKE = "intake"
    DOCUMENTS_PENDING = "documents_pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    FILED = "filed"
    CLOSED = "closed"


class Client(BaseModel):
    """Client model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_code: str = Field(max_length=10)
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ClientCreate(BaseModel):
    """Schema for creating a new client."""

    client_code: str = Field(max_length=10)
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    notes: str | None = None


class Case(BaseModel):
    """Tax case model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    client_code: str
    client_name: str
    tax_year: int = Field(ge=2000, le=2100)
    case_type: CaseType
    status: CaseStatus = CaseStatus.INTAKE
    notes: str | None = None
    document_count: int = 0
    artifact_count: int = 0
    created_at: datetime
    updated_at: datetime


class CaseCreate(BaseModel):
    """Schema for creating a new case."""

    client_code: str = Field(max_length=10)
    tax_year: int = Field(ge=2000, le=2100)
    case_type: CaseType = CaseType.TAX_RETURN
    notes: str | None = None


class CaseUpdate(BaseModel):
    """Schema for updating a case."""

    status: CaseStatus | None = None
    notes: str | None = None


class CaseSummary(BaseModel):
    """Summary of case for quick views."""

    id: UUID
    client_code: str
    client_name: str
    tax_year: int
    case_type: CaseType
    status: CaseStatus
    document_count: int
    artifact_count: int
    updated_at: datetime
