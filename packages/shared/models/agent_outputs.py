"""Strictly typed agent output schemas.

All agent outputs MUST conform to these schemas.
UI renders based on schema, not freeform text.
"""

from datetime import date
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from shared.models.document import Citation


class ConfidenceLevel(str, Enum):
    """Confidence level for extracted values."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExtractedField(BaseModel):
    """A single extracted field with confidence."""

    name: str
    value: str | Decimal | int | None
    confidence: ConfidenceLevel
    source_page: int | None = None
    notes: str | None = None


class W2Extraction(BaseModel):
    """Extracted W-2 data."""

    employer_name: str | None = None
    employer_ein: str | None = None
    employer_address: str | None = None
    employee_ssn_last4: str | None = None
    wages: Decimal | None = None
    federal_tax_withheld: Decimal | None = None
    social_security_wages: Decimal | None = None
    social_security_tax: Decimal | None = None
    medicare_wages: Decimal | None = None
    medicare_tax: Decimal | None = None
    state: str | None = None
    state_wages: Decimal | None = None
    state_tax_withheld: Decimal | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    anomalies: list[str] = Field(default_factory=list)


class Form1099Extraction(BaseModel):
    """Extracted 1099 data (INT, DIV, B, etc.)."""

    form_type: str  # 1099-INT, 1099-DIV, 1099-B, etc.
    payer_name: str | None = None
    payer_tin: str | None = None
    recipient_ssn_last4: str | None = None
    amount: Decimal | None = None
    federal_tax_withheld: Decimal | None = None
    state: str | None = None
    state_tax_withheld: Decimal | None = None
    additional_fields: dict[str, str | Decimal] = Field(default_factory=dict)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    anomalies: list[str] = Field(default_factory=list)


class K1Extraction(BaseModel):
    """Extracted K-1 data."""

    partnership_name: str | None = None
    partnership_ein: str | None = None
    partner_ssn_last4: str | None = None
    ordinary_income: Decimal | None = None
    rental_income: Decimal | None = None
    interest_income: Decimal | None = None
    dividend_income: Decimal | None = None
    capital_gain: Decimal | None = None
    section_179: Decimal | None = None
    other_income: dict[str, Decimal] = Field(default_factory=dict)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    anomalies: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Complete extraction result from Document Extraction Agent."""

    document_id: UUID
    document_type: str  # W2, 1099-INT, K1, etc.
    extracted_at: str  # ISO timestamp
    w2: W2Extraction | None = None
    form_1099: Form1099Extraction | None = None
    k1: K1Extraction | None = None
    raw_fields: list[ExtractedField] = Field(default_factory=list)
    overall_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    anomalies: list[str] = Field(default_factory=list)
    needs_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)


class FirmKnowledgeResponse(BaseModel):
    """Output from Firm Knowledge Agent."""

    answer: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    related_topics: list[str] = Field(default_factory=list)
    needs_human_review: bool = False


class MissingDocItem(BaseModel):
    """A single missing document item."""

    name: str
    description: str | None = None
    priority: str = "normal"  # high, normal, low
    category: str | None = None  # income, deductions, credits, etc.


class MissingDocsEmail(BaseModel):
    """Output from Intake/Missing Docs Agent."""

    client_name: str
    tax_year: int
    missing_items: list[MissingDocItem]
    email_subject: str
    email_body: str
    deadline: date | None = None
    preparer_name: str
    firm_name: str


class OrganizerChecklist(BaseModel):
    """Output for organizer checklist generation."""

    client_name: str
    tax_year: int
    return_type: str  # individual, business
    sections: list[dict[str, list[str]]]  # section name -> items
    custom_items: list[MissingDocItem] = Field(default_factory=list)


class NoticeResponsePoint(BaseModel):
    """A single point in a notice response."""

    item: str
    response: str
    supporting_docs: list[str] = Field(default_factory=list)


class AttachmentItem(BaseModel):
    """An attachment for a notice response."""

    name: str
    description: str | None = None
    document_id: UUID | None = None


class NoticeResponse(BaseModel):
    """Output from IRS Notice Response Agent."""

    client_name: str
    ssn_last4: str
    notice_type: str  # CP2000, CP2501, LT11, etc.
    notice_date: str
    tax_year: int
    response_points: list[NoticeResponsePoint]
    attachments: list[AttachmentItem] = Field(default_factory=list)
    needed_info: list[str] = Field(default_factory=list)
    preparer_name: str
    firm_name: str
    firm_address: str
    draft_letter: str


class QCFinding(BaseModel):
    """A single QC finding."""

    severity: str  # error, warning, info
    category: str  # completeness, accuracy, consistency, etc.
    description: str
    location: str | None = None  # document/field reference
    recommendation: str | None = None


class QCReport(BaseModel):
    """Output from QC Agent."""

    case_id: UUID
    client_name: str
    tax_year: int
    checked_at: str  # ISO timestamp
    findings: list[QCFinding] = Field(default_factory=list)
    missing_documents: list[str] = Field(default_factory=list)
    data_anomalies: list[str] = Field(default_factory=list)
    pass_status: bool = True
    summary: str
    reviewer_notes: str | None = None
