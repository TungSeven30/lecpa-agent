"""Document extraction subagent.

Extracts structured data from tax documents (W-2, 1099, K-1) using LLM analysis.
Returns typed Pydantic models with confidence scores and anomaly detection.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

import orjson
import structlog
from database.models import Artifact, Document, DocumentChunk
from services.model_router import ModelRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.agent_outputs import (
    ConfidenceLevel,
    ExtractedField,
    ExtractionResult,
    Form1099Extraction,
    K1Extraction,
    W2Extraction,
)

logger = structlog.get_logger()


class ExtractionAgent:
    """Subagent for extracting structured data from tax documents.

    Responsibilities:
    - Extract field values from W-2, 1099, and K-1 documents
    - Validate extracted data and detect anomalies
    - Calculate confidence scores per field
    - Store extraction results as artifacts

    Example:
        agent = ExtractionAgent(model_router)
        result = await agent.extract_document(document_id, db)
        # result.w2.wages = Decimal("85000.00")
    """

    W2_SYSTEM_PROMPT = """You are a document extraction specialist for a CPA firm.
Extract all fields from this W-2 form into a JSON object.

Required fields to extract:
- employer_name: Company name from Box c
- employer_ein: Employer ID number from Box b (format: XX-XXXXXXX)
- employer_address: Full address from Box c
- employee_ssn_last4: Last 4 digits ONLY of SSN from Box a
- wages: Box 1 - Wages, tips, other compensation
- federal_tax_withheld: Box 2 - Federal income tax withheld
- social_security_wages: Box 3 - Social security wages
- social_security_tax: Box 4 - Social security tax withheld
- medicare_wages: Box 5 - Medicare wages and tips
- medicare_tax: Box 6 - Medicare tax withheld
- state: Box 15 - State
- state_wages: Box 16 - State wages
- state_tax_withheld: Box 17 - State income tax

Output format:
{
  "employer_name": "string or null",
  "employer_ein": "XX-XXXXXXX or null",
  "employer_address": "string or null",
  "employee_ssn_last4": "1234 (4 digits only)",
  "wages": 85000.00,
  "federal_tax_withheld": 12500.00,
  "social_security_wages": 85000.00,
  "social_security_tax": 5270.00,
  "medicare_wages": 85000.00,
  "medicare_tax": 1232.50,
  "state": "CA",
  "state_wages": 85000.00,
  "state_tax_withheld": 4250.00,
  "confidence": "HIGH/MEDIUM/LOW",
  "anomalies": ["list of issues found"]
}

Rules:
- Use null for fields that cannot be found
- Use numeric values (not strings) for dollar amounts
- Only extract the LAST 4 digits of SSN - never the full SSN
- Flag anomalies like: negative values, tax > wages, missing required fields
- Set confidence to HIGH if all key fields found clearly, MEDIUM if some unclear, LOW if many missing

Respond with ONLY the JSON object."""

    FORM_1099_SYSTEM_PROMPT = """You are a document extraction specialist for a CPA firm.
Extract all fields from this 1099 form into a JSON object.

First identify the 1099 type (INT, DIV, B, MISC, NEC, R, etc.)

Common fields across types:
- form_type: "1099-INT", "1099-DIV", "1099-B", etc.
- payer_name: Name of the payer/institution
- payer_tin: Payer's TIN (format: XX-XXXXXXX)
- recipient_ssn_last4: Last 4 digits ONLY of recipient SSN
- amount: Primary amount (interest, dividends, gross proceeds, etc.)
- federal_tax_withheld: Federal tax withheld if any
- state: State code if present
- state_tax_withheld: State tax withheld if any

Type-specific fields go in additional_fields:
- 1099-INT: interest_income, early_withdrawal_penalty, tax_exempt_interest
- 1099-DIV: ordinary_dividends, qualified_dividends, capital_gain_distributions
- 1099-B: gross_proceeds, cost_basis, gain_loss, wash_sale_loss
- 1099-MISC: rents, royalties, other_income
- 1099-NEC: nonemployee_compensation

Output format:
{
  "form_type": "1099-INT",
  "payer_name": "string or null",
  "payer_tin": "XX-XXXXXXX or null",
  "recipient_ssn_last4": "1234",
  "amount": 1500.00,
  "federal_tax_withheld": 0.00,
  "state": "CA or null",
  "state_tax_withheld": null,
  "additional_fields": {
    "interest_income": 1500.00,
    "tax_exempt_interest": 0.00
  },
  "confidence": "HIGH/MEDIUM/LOW",
  "anomalies": []
}

Rules:
- Only extract LAST 4 digits of SSN
- Use null for fields not present
- Flag anomalies: negative amounts, inconsistent totals

Respond with ONLY the JSON object."""

    K1_SYSTEM_PROMPT = """You are a document extraction specialist for a CPA firm.
Extract all fields from this Schedule K-1 form into a JSON object.

Key fields to extract:
- partnership_name: Name of partnership/S-corp/estate
- partnership_ein: Partnership EIN (format: XX-XXXXXXX)
- partner_ssn_last4: Last 4 digits ONLY of partner/shareholder SSN
- ordinary_income: Box 1 (1065) or Box 1 (1120S) - Ordinary business income
- rental_income: Box 2 - Net rental real estate income
- interest_income: Box 5 - Interest income
- dividend_income: Box 6a - Ordinary dividends
- capital_gain: Box 8/9 - Net short/long-term capital gain
- section_179: Box 11 or 12 - Section 179 deduction
- other_income: Dictionary of other income items

Output format:
{
  "partnership_name": "string or null",
  "partnership_ein": "XX-XXXXXXX or null",
  "partner_ssn_last4": "1234",
  "ordinary_income": 25000.00,
  "rental_income": null,
  "interest_income": 500.00,
  "dividend_income": 1200.00,
  "capital_gain": 3500.00,
  "section_179": null,
  "other_income": {
    "guaranteed_payments": 12000.00
  },
  "confidence": "HIGH/MEDIUM/LOW",
  "anomalies": []
}

Rules:
- K-1s are complex; extract what's clearly visible
- Use null for empty/missing fields
- Only extract LAST 4 digits of SSN
- Flag anomalies: missing EIN, negative values where unexpected

Respond with ONLY the JSON object."""

    def __init__(self, model_router: ModelRouter) -> None:
        """Initialize the extraction agent.

        Args:
            model_router: Router for LLM calls
        """
        self.model_router = model_router

    async def extract_document(
        self,
        document_id: UUID,
        db: AsyncSession,
        document_type: str | None = None,
    ) -> ExtractionResult:
        """Extract structured data from a document.

        Auto-detects document type from tags if not specified.
        Routes to appropriate extraction method.

        Args:
            document_id: Document to extract from
            db: Database session
            document_type: Optional type override (W2, 1099, K1)

        Returns:
            ExtractionResult with typed extraction data

        Raises:
            ValueError: If document not found or unsupported type
        """
        # Get document and its text
        document = await db.get(Document, document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Get document text from chunks
        document_text = await self._get_document_text(document_id, db)
        if not document_text:
            raise ValueError(f"No text found for document: {document_id}")

        # Determine document type from tags if not specified
        if not document_type:
            document_type = self._detect_document_type(document.tags)

        logger.info(
            "Extracting document",
            document_id=str(document_id),
            document_type=document_type,
            text_length=len(document_text),
        )

        # Route to appropriate extraction method
        if document_type == "W2":
            result = await self.extract_w2(document_id, document_text, db)
        elif document_type.startswith("1099"):
            result = await self.extract_1099(document_id, document_text, db)
        elif document_type == "K1":
            result = await self.extract_k1(document_id, document_text, db)
        else:
            # Generic extraction for unrecognized types
            result = await self._extract_generic(document_id, document_text, document_type, db)

        # Store as artifact
        await self._store_extraction_artifact(result, document, db)

        return result

    async def extract_w2(
        self,
        document_id: UUID,
        document_text: str,
        _db: AsyncSession,
    ) -> ExtractionResult:
        """Extract W-2 data from document text.

        Args:
            document_id: Document identifier
            document_text: Raw document text
            _db: Database session (reserved for future use)

        Returns:
            ExtractionResult with W2Extraction populated
        """
        prompt = f"""Extract all fields from this W-2 document.

Document text:
{document_text}

Extract the fields and respond with JSON only."""

        response = await self.model_router.generate(
            task="extraction",
            messages=[{"role": "user", "content": prompt}],
            system=self.W2_SYSTEM_PROMPT,
            temperature=0.0,
        )

        # Parse JSON response
        try:
            data = orjson.loads(response)
        except orjson.JSONDecodeError as e:
            logger.error("Failed to parse W-2 extraction JSON", error=str(e))
            return self._create_failed_result(document_id, "W2", str(e))

        # Build W2Extraction model
        w2 = W2Extraction(
            employer_name=data.get("employer_name"),
            employer_ein=data.get("employer_ein"),
            employer_address=data.get("employer_address"),
            employee_ssn_last4=data.get("employee_ssn_last4"),
            wages=self._parse_decimal(data.get("wages")),
            federal_tax_withheld=self._parse_decimal(data.get("federal_tax_withheld")),
            social_security_wages=self._parse_decimal(data.get("social_security_wages")),
            social_security_tax=self._parse_decimal(data.get("social_security_tax")),
            medicare_wages=self._parse_decimal(data.get("medicare_wages")),
            medicare_tax=self._parse_decimal(data.get("medicare_tax")),
            state=data.get("state"),
            state_wages=self._parse_decimal(data.get("state_wages")),
            state_tax_withheld=self._parse_decimal(data.get("state_tax_withheld")),
            confidence=self._parse_confidence(data.get("confidence", "MEDIUM")),
            anomalies=data.get("anomalies", []),
        )

        # Run additional anomaly detection
        w2.anomalies.extend(self._detect_w2_anomalies(w2))

        # Determine overall confidence and review needs
        overall_confidence = w2.confidence
        needs_review = (
            overall_confidence == ConfidenceLevel.LOW
            or len(w2.anomalies) > 0
            or w2.wages is None
        )

        return ExtractionResult(
            document_id=document_id,
            document_type="W2",
            extracted_at=datetime.now().isoformat(),
            w2=w2,
            overall_confidence=overall_confidence,
            anomalies=w2.anomalies,
            needs_review=needs_review,
            review_reasons=w2.anomalies if needs_review else [],
        )

    async def extract_1099(
        self,
        document_id: UUID,
        document_text: str,
        _db: AsyncSession,
    ) -> ExtractionResult:
        """Extract 1099 data from document text.

        Args:
            document_id: Document identifier
            document_text: Raw document text
            _db: Database session (reserved for future use)

        Returns:
            ExtractionResult with Form1099Extraction populated
        """
        prompt = f"""Extract all fields from this 1099 document.

Document text:
{document_text}

Identify the 1099 type and extract all relevant fields. Respond with JSON only."""

        response = await self.model_router.generate(
            task="extraction",
            messages=[{"role": "user", "content": prompt}],
            system=self.FORM_1099_SYSTEM_PROMPT,
            temperature=0.0,
        )

        try:
            data = orjson.loads(response)
        except orjson.JSONDecodeError as e:
            logger.error("Failed to parse 1099 extraction JSON", error=str(e))
            return self._create_failed_result(document_id, "1099", str(e))

        form_type = data.get("form_type", "1099")

        # Parse additional fields, converting values to Decimal where appropriate
        additional_fields: dict[str, str | Decimal] = {}
        for key, value in data.get("additional_fields", {}).items():
            if isinstance(value, (int, float)):
                additional_fields[key] = Decimal(str(value))
            else:
                additional_fields[key] = value

        form_1099 = Form1099Extraction(
            form_type=form_type,
            payer_name=data.get("payer_name"),
            payer_tin=data.get("payer_tin"),
            recipient_ssn_last4=data.get("recipient_ssn_last4"),
            amount=self._parse_decimal(data.get("amount")),
            federal_tax_withheld=self._parse_decimal(data.get("federal_tax_withheld")),
            state=data.get("state"),
            state_tax_withheld=self._parse_decimal(data.get("state_tax_withheld")),
            additional_fields=additional_fields,
            confidence=self._parse_confidence(data.get("confidence", "MEDIUM")),
            anomalies=data.get("anomalies", []),
        )

        # Run additional anomaly detection
        form_1099.anomalies.extend(self._detect_1099_anomalies(form_1099))

        overall_confidence = form_1099.confidence
        needs_review = (
            overall_confidence == ConfidenceLevel.LOW
            or len(form_1099.anomalies) > 0
        )

        return ExtractionResult(
            document_id=document_id,
            document_type=form_type,
            extracted_at=datetime.now().isoformat(),
            form_1099=form_1099,
            overall_confidence=overall_confidence,
            anomalies=form_1099.anomalies,
            needs_review=needs_review,
            review_reasons=form_1099.anomalies if needs_review else [],
        )

    async def extract_k1(
        self,
        document_id: UUID,
        document_text: str,
        _db: AsyncSession,
    ) -> ExtractionResult:
        """Extract K-1 data from document text.

        Args:
            document_id: Document identifier
            document_text: Raw document text
            _db: Database session (reserved for future use)

        Returns:
            ExtractionResult with K1Extraction populated
        """
        prompt = f"""Extract all fields from this Schedule K-1 document.

Document text:
{document_text}

Extract all income and deduction fields. Respond with JSON only."""

        response = await self.model_router.generate(
            task="extraction",
            messages=[{"role": "user", "content": prompt}],
            system=self.K1_SYSTEM_PROMPT,
            temperature=0.0,
        )

        try:
            data = orjson.loads(response)
        except orjson.JSONDecodeError as e:
            logger.error("Failed to parse K-1 extraction JSON", error=str(e))
            return self._create_failed_result(document_id, "K1", str(e))

        # Parse other_income dict
        other_income: dict[str, Decimal] = {}
        for key, value in data.get("other_income", {}).items():
            parsed = self._parse_decimal(value)
            if parsed is not None:
                other_income[key] = parsed

        k1 = K1Extraction(
            partnership_name=data.get("partnership_name"),
            partnership_ein=data.get("partnership_ein"),
            partner_ssn_last4=data.get("partner_ssn_last4"),
            ordinary_income=self._parse_decimal(data.get("ordinary_income")),
            rental_income=self._parse_decimal(data.get("rental_income")),
            interest_income=self._parse_decimal(data.get("interest_income")),
            dividend_income=self._parse_decimal(data.get("dividend_income")),
            capital_gain=self._parse_decimal(data.get("capital_gain")),
            section_179=self._parse_decimal(data.get("section_179")),
            other_income=other_income,
            confidence=self._parse_confidence(data.get("confidence", "MEDIUM")),
            anomalies=data.get("anomalies", []),
        )

        # Run additional anomaly detection
        k1.anomalies.extend(self._detect_k1_anomalies(k1))

        overall_confidence = k1.confidence
        needs_review = (
            overall_confidence == ConfidenceLevel.LOW
            or len(k1.anomalies) > 0
            or k1.partnership_ein is None
        )

        return ExtractionResult(
            document_id=document_id,
            document_type="K1",
            extracted_at=datetime.now().isoformat(),
            k1=k1,
            overall_confidence=overall_confidence,
            anomalies=k1.anomalies,
            needs_review=needs_review,
            review_reasons=k1.anomalies if needs_review else [],
        )

    async def _extract_generic(
        self,
        document_id: UUID,
        document_text: str,
        document_type: str,
        _db: AsyncSession,
    ) -> ExtractionResult:
        """Generic extraction for unrecognized document types.

        Returns raw extracted fields without typed schema.
        """
        prompt = f"""Extract all structured data from this {document_type} document.

Document text:
{document_text}

Return a JSON object with:
- fields: array of {{name, value, confidence}} objects
- anomalies: array of any issues found
- overall_confidence: HIGH/MEDIUM/LOW"""

        response = await self.model_router.generate(
            task="extraction",
            messages=[{"role": "user", "content": prompt}],
            system="Extract structured data from documents. Return JSON only.",
            temperature=0.0,
        )

        try:
            data = orjson.loads(response)
        except orjson.JSONDecodeError:
            data = {"fields": [], "anomalies": ["Failed to parse extraction"], "overall_confidence": "LOW"}

        raw_fields = [
            ExtractedField(
                name=f.get("name", "unknown"),
                value=f.get("value"),
                confidence=self._parse_confidence(f.get("confidence", "MEDIUM")),
            )
            for f in data.get("fields", [])
        ]

        return ExtractionResult(
            document_id=document_id,
            document_type=document_type,
            extracted_at=datetime.now().isoformat(),
            raw_fields=raw_fields,
            overall_confidence=self._parse_confidence(data.get("overall_confidence", "LOW")),
            anomalies=data.get("anomalies", []),
            needs_review=True,
            review_reasons=["Generic extraction - manual review recommended"],
        )

    async def _get_document_text(
        self,
        document_id: UUID,
        db: AsyncSession,
    ) -> str:
        """Retrieve full document text from chunks.

        Args:
            document_id: Document identifier
            db: Database session

        Returns:
            Concatenated text from all chunks
        """
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        result = await db.execute(stmt)
        chunks = result.scalars().all()

        if not chunks:
            return ""

        return "\n\n".join(chunk.content for chunk in chunks)

    async def _store_extraction_artifact(
        self,
        result: ExtractionResult,
        document: Document,
        db: AsyncSession,
    ) -> Artifact:
        """Store extraction result as an artifact.

        Args:
            result: Extraction result to store
            document: Source document
            db: Database session

        Returns:
            Created artifact
        """
        # Format content as markdown summary
        content = self._format_extraction_summary(result, document.filename)

        artifact = Artifact(
            case_id=document.case_id,
            artifact_type="extraction_result",
            title=f"Extraction: {document.filename}",
            content=content,
            content_format="markdown",
            is_draft=False,
            created_by="extraction_agent",
        )

        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)

        logger.info(
            "Stored extraction artifact",
            document_id=str(document.id),
            artifact_id=str(artifact.id),
            document_type=result.document_type,
            confidence=result.overall_confidence.value,
        )

        return artifact

    def _format_extraction_summary(
        self,
        result: ExtractionResult,
        filename: str,
    ) -> str:
        """Format extraction result as markdown.

        Args:
            result: Extraction result
            filename: Source document filename

        Returns:
            Markdown formatted summary
        """
        lines = [
            f"# Extraction Summary: {filename}",
            "",
            f"**Document Type:** {result.document_type}",
            f"**Extracted At:** {result.extracted_at}",
            f"**Confidence:** {result.overall_confidence.value.upper()}",
            f"**Needs Review:** {'Yes' if result.needs_review else 'No'}",
            "",
        ]

        # Add type-specific fields
        if result.w2:
            lines.extend(self._format_w2_fields(result.w2))
        elif result.form_1099:
            lines.extend(self._format_1099_fields(result.form_1099))
        elif result.k1:
            lines.extend(self._format_k1_fields(result.k1))
        elif result.raw_fields:
            lines.append("## Extracted Fields")
            lines.append("")
            for field in result.raw_fields:
                lines.append(f"- **{field.name}:** {field.value} ({field.confidence.value})")

        # Add anomalies
        if result.anomalies:
            lines.extend(["", "## Anomalies", ""])
            for anomaly in result.anomalies:
                lines.append(f"- ⚠️ {anomaly}")

        if result.review_reasons:
            lines.extend(["", "## Review Reasons", ""])
            for reason in result.review_reasons:
                lines.append(f"- {reason}")

        return "\n".join(lines)

    def _format_w2_fields(self, w2: W2Extraction) -> list[str]:
        """Format W-2 fields as markdown lines."""
        return [
            "## W-2 Fields",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| Employer | {w2.employer_name or 'N/A'} |",
            f"| Employer EIN | {w2.employer_ein or 'N/A'} |",
            f"| Employee SSN (last 4) | {w2.employee_ssn_last4 or 'N/A'} |",
            f"| Wages (Box 1) | ${w2.wages:,.2f} |" if w2.wages else "| Wages (Box 1) | N/A |",
            f"| Federal Tax Withheld (Box 2) | ${w2.federal_tax_withheld:,.2f} |" if w2.federal_tax_withheld else "| Federal Tax Withheld (Box 2) | N/A |",
            f"| Social Security Wages (Box 3) | ${w2.social_security_wages:,.2f} |" if w2.social_security_wages else "| Social Security Wages (Box 3) | N/A |",
            f"| Social Security Tax (Box 4) | ${w2.social_security_tax:,.2f} |" if w2.social_security_tax else "| Social Security Tax (Box 4) | N/A |",
            f"| Medicare Wages (Box 5) | ${w2.medicare_wages:,.2f} |" if w2.medicare_wages else "| Medicare Wages (Box 5) | N/A |",
            f"| Medicare Tax (Box 6) | ${w2.medicare_tax:,.2f} |" if w2.medicare_tax else "| Medicare Tax (Box 6) | N/A |",
            f"| State | {w2.state or 'N/A'} |",
            f"| State Wages | ${w2.state_wages:,.2f} |" if w2.state_wages else "| State Wages | N/A |",
            f"| State Tax Withheld | ${w2.state_tax_withheld:,.2f} |" if w2.state_tax_withheld else "| State Tax Withheld | N/A |",
            "",
        ]

    def _format_1099_fields(self, form_1099: Form1099Extraction) -> list[str]:
        """Format 1099 fields as markdown lines."""
        lines = [
            "## 1099 Fields",
            "",
            f"**Form Type:** {form_1099.form_type}",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| Payer | {form_1099.payer_name or 'N/A'} |",
            f"| Payer TIN | {form_1099.payer_tin or 'N/A'} |",
            f"| Recipient SSN (last 4) | {form_1099.recipient_ssn_last4 or 'N/A'} |",
            f"| Amount | ${form_1099.amount:,.2f} |" if form_1099.amount else "| Amount | N/A |",
            f"| Federal Tax Withheld | ${form_1099.federal_tax_withheld:,.2f} |" if form_1099.federal_tax_withheld else "| Federal Tax Withheld | N/A |",
        ]

        if form_1099.additional_fields:
            lines.extend(["", "### Additional Fields", ""])
            for key, value in form_1099.additional_fields.items():
                if isinstance(value, Decimal):
                    lines.append(f"- **{key}:** ${value:,.2f}")
                else:
                    lines.append(f"- **{key}:** {value}")

        lines.append("")
        return lines

    def _format_k1_fields(self, k1: K1Extraction) -> list[str]:
        """Format K-1 fields as markdown lines."""
        lines = [
            "## K-1 Fields",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| Partnership/Entity | {k1.partnership_name or 'N/A'} |",
            f"| Partnership EIN | {k1.partnership_ein or 'N/A'} |",
            f"| Partner SSN (last 4) | {k1.partner_ssn_last4 or 'N/A'} |",
            f"| Ordinary Income | ${k1.ordinary_income:,.2f} |" if k1.ordinary_income else "| Ordinary Income | N/A |",
            f"| Rental Income | ${k1.rental_income:,.2f} |" if k1.rental_income else "| Rental Income | N/A |",
            f"| Interest Income | ${k1.interest_income:,.2f} |" if k1.interest_income else "| Interest Income | N/A |",
            f"| Dividend Income | ${k1.dividend_income:,.2f} |" if k1.dividend_income else "| Dividend Income | N/A |",
            f"| Capital Gain | ${k1.capital_gain:,.2f} |" if k1.capital_gain else "| Capital Gain | N/A |",
            f"| Section 179 | ${k1.section_179:,.2f} |" if k1.section_179 else "| Section 179 | N/A |",
        ]

        if k1.other_income:
            lines.extend(["", "### Other Income", ""])
            for key, value in k1.other_income.items():
                lines.append(f"- **{key}:** ${value:,.2f}")

        lines.append("")
        return lines

    def _detect_document_type(self, tags: list[str]) -> str:
        """Detect document type from tags.

        Args:
            tags: Document tags

        Returns:
            Document type string (W2, 1099, K1, or UNKNOWN)
        """
        tags_upper = [t.upper() for t in tags]

        if "W2" in tags_upper:
            return "W2"
        elif any("1099" in t for t in tags_upper):
            return "1099"
        elif "K1" in tags_upper:
            return "K1"
        else:
            return "UNKNOWN"

    def _parse_decimal(self, value: str | int | float | None) -> Decimal | None:
        """Parse a value to Decimal.

        Args:
            value: Value to parse

        Returns:
            Decimal or None if invalid
        """
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    def _parse_confidence(self, value: str) -> ConfidenceLevel:
        """Parse confidence level from string.

        Args:
            value: Confidence string (HIGH/MEDIUM/LOW)

        Returns:
            ConfidenceLevel enum
        """
        mapping = {
            "HIGH": ConfidenceLevel.HIGH,
            "MEDIUM": ConfidenceLevel.MEDIUM,
            "LOW": ConfidenceLevel.LOW,
            "high": ConfidenceLevel.HIGH,
            "medium": ConfidenceLevel.MEDIUM,
            "low": ConfidenceLevel.LOW,
        }
        return mapping.get(value, ConfidenceLevel.MEDIUM)

    def _create_failed_result(
        self,
        document_id: UUID,
        document_type: str,
        error: str,
    ) -> ExtractionResult:
        """Create a failed extraction result.

        Args:
            document_id: Document identifier
            document_type: Document type
            error: Error message

        Returns:
            ExtractionResult with failure info
        """
        return ExtractionResult(
            document_id=document_id,
            document_type=document_type,
            extracted_at=datetime.now().isoformat(),
            overall_confidence=ConfidenceLevel.LOW,
            anomalies=[f"Extraction failed: {error}"],
            needs_review=True,
            review_reasons=[f"Extraction failed: {error}"],
        )

    def _detect_w2_anomalies(self, w2: W2Extraction) -> list[str]:
        """Detect anomalies in W-2 data.

        Args:
            w2: W-2 extraction

        Returns:
            List of anomaly descriptions
        """
        anomalies = []

        # Negative values
        if w2.wages is not None and w2.wages < 0:
            anomalies.append("Negative wages detected")

        if w2.federal_tax_withheld is not None and w2.federal_tax_withheld < 0:
            anomalies.append("Negative federal tax withheld")

        # Tax exceeds wages (implausible)
        if (
            w2.wages is not None
            and w2.federal_tax_withheld is not None
            and w2.federal_tax_withheld > w2.wages
        ):
            anomalies.append("Federal tax withheld exceeds wages")

        # Social Security tax validation (should be ~6.2% of wages up to limit)
        if w2.social_security_wages is not None and w2.social_security_tax is not None:
            expected_ss_tax = w2.social_security_wages * Decimal("0.062")
            if w2.social_security_tax > expected_ss_tax * Decimal("1.1"):
                anomalies.append("Social Security tax appears higher than expected")

        # Missing critical fields
        if w2.wages is None:
            anomalies.append("Missing wages (Box 1)")

        if w2.employer_ein is None:
            anomalies.append("Missing employer EIN")

        return anomalies

    def _detect_1099_anomalies(self, form_1099: Form1099Extraction) -> list[str]:
        """Detect anomalies in 1099 data.

        Args:
            form_1099: 1099 extraction

        Returns:
            List of anomaly descriptions
        """
        anomalies = []

        if form_1099.amount is not None and form_1099.amount < 0:
            anomalies.append("Negative amount detected")

        if form_1099.federal_tax_withheld is not None:
            if form_1099.federal_tax_withheld < 0:
                anomalies.append("Negative federal tax withheld")
            if (
                form_1099.amount is not None
                and form_1099.federal_tax_withheld > form_1099.amount
            ):
                anomalies.append("Federal tax withheld exceeds amount")

        if form_1099.payer_name is None:
            anomalies.append("Missing payer name")

        return anomalies

    def _detect_k1_anomalies(self, k1: K1Extraction) -> list[str]:
        """Detect anomalies in K-1 data.

        Args:
            k1: K-1 extraction

        Returns:
            List of anomaly descriptions
        """
        anomalies = []

        if k1.partnership_ein is None:
            anomalies.append("Missing partnership EIN")

        if k1.partnership_name is None:
            anomalies.append("Missing partnership name")

        # Check for any income fields being present
        income_fields = [
            k1.ordinary_income,
            k1.rental_income,
            k1.interest_income,
            k1.dividend_income,
            k1.capital_gain,
        ]
        if all(f is None for f in income_fields) and not k1.other_income:
            anomalies.append("No income fields extracted - document may be unreadable")

        return anomalies
