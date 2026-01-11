"""IRS Notice Response subagent.

Analyzes IRS notices and generates professional response letters with
supporting documentation recommendations.
"""

from datetime import datetime
from uuid import UUID

import orjson
import structlog
from database.models import Artifact, Document, DocumentChunk
from services.model_router import ModelRouter
from services.template_renderer import get_template_renderer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.agent_outputs import (
    AttachmentItem,
    NoticeResponse,
    NoticeResponsePoint,
)

logger = structlog.get_logger()


class NoticeAgent:
    """Subagent for IRS notice analysis and response generation.

    Responsibilities:
    - Analyze IRS notices to identify type, issues, and deadlines
    - Generate professional response letters
    - Recommend supporting documentation
    - Flag missing information needed from client

    Example:
        agent = NoticeAgent(model_router)
        result = await agent.draft_notice_response(case_id, notice_doc_id, db)
        # result.draft_letter contains the response letter
    """

    SYSTEM_PROMPT = """You are an IRS notice response specialist for a CPA firm.

Your responsibilities:
1. Analyze IRS notices to identify the notice type and issues
2. Draft professional response letters addressing each issue
3. Recommend supporting documentation to include
4. Identify any missing information needed from the client

Common IRS Notice Types:
- CP2000: Underreported income - IRS found income not reported on return
- CP2501: Proposed changes to return - Similar to CP2000, proposed adjustments
- CP501/CP503/CP504: Balance due notices - Unpaid tax balance with increasing urgency
- CP11/CP12: Math error notices - IRS corrected calculation errors
- CP14: Balance due - First notice of unpaid tax
- CP22A: Changes to tax return - IRS made changes, balance may be due
- CP49: Refund applied to debt - Refund used to pay another balance
- CP59/CP515: Request for tax return - IRS has no record of filed return
- LT11/LT1058: Intent to levy - Serious collection action pending

Response Guidelines:
- Be professional and respectful but firm
- Address each issue raised in the notice specifically
- Reference specific tax code sections when applicable
- Always recommend relevant supporting documentation
- Flag items that need client information before responding

Output your analysis as JSON in this exact format:
{
  "notice_type": "CP2000",
  "notice_summary": "Brief description of what the notice is about",
  "issues": [
    {
      "item": "Description of the issue (e.g., 'Unreported 1099-INT income')",
      "response": "Professional response addressing this issue",
      "supporting_docs": ["List of documents to support this response"]
    }
  ],
  "attachments_needed": [
    {"name": "Document name", "description": "Why it's needed"}
  ],
  "missing_info": ["List of information needed from client"],
  "deadline": "YYYY-MM-DD or null if not specified",
  "amount_due": 1234.56,
  "confidence": "HIGH/MEDIUM/LOW"
}

Respond with ONLY the JSON object."""

    NOTICE_TYPE_PROMPTS = {
        "CP2000": """This is a CP2000 notice (Underreported Income).
The IRS is proposing changes because they received information (W-2s, 1099s) that doesn't match the return.
Common responses:
- Income was reported on a different line
- Income was reported on a different return (married filing separately)
- The 1099 amount is incorrect (get corrected 1099)
- Income is not taxable (explain why)
- Already filed amended return""",

        "CP501": """This is a CP501 (Balance Due Reminder).
First reminder that taxes are owed. Response options:
- Payment in full
- Installment agreement request
- Dispute the balance (provide documentation)
- Penalty abatement request (reasonable cause)""",

        "CP504": """This is a CP504 (Intent to Levy).
Serious notice - IRS may levy bank accounts/wages within 30 days.
Immediate action needed:
- Pay balance to stop levy
- Set up installment agreement
- Request Currently Not Collectible status
- File Collection Due Process appeal if disputing""",

        "LT11": """This is an LT11 (Final Notice - Intent to Levy).
Last notice before levy action. Client has 30 days to:
- Pay in full
- Request Collection Due Process hearing
- Set up payment plan
- Apply for Offer in Compromise""",
    }

    def __init__(self, model_router: ModelRouter) -> None:
        """Initialize the notice agent.

        Args:
            model_router: Router for LLM calls
        """
        self.model_router = model_router
        self.renderer = get_template_renderer()

    async def analyze_notice(
        self,
        document_id: UUID,
        db: AsyncSession,
    ) -> dict:
        """Analyze an IRS notice document.

        Args:
            document_id: Notice document to analyze
            db: Database session

        Returns:
            Dictionary with notice type, issues, and recommendations
        """
        document = await db.get(Document, document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        document_text = await self._get_document_text(document_id, db)
        if not document_text:
            raise ValueError(f"No text found for document: {document_id}")

        logger.info(
            "Analyzing IRS notice",
            document_id=str(document_id),
            text_length=len(document_text),
        )

        prompt = f"""Analyze this IRS notice and extract all relevant information.

Notice text:
{document_text}

Identify the notice type, issues, deadlines, and amounts. Respond with JSON only."""

        response = await self.model_router.generate(
            task="extraction",
            messages=[{"role": "user", "content": prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.0,
        )

        try:
            analysis = orjson.loads(response)
        except orjson.JSONDecodeError as e:
            logger.error("Failed to parse notice analysis JSON", error=str(e))
            analysis = {
                "notice_type": "UNKNOWN",
                "notice_summary": "Unable to parse notice",
                "issues": [],
                "attachments_needed": [],
                "missing_info": ["Manual review required - notice could not be parsed"],
                "confidence": "LOW",
            }

        return analysis

    async def draft_notice_response(
        self,
        case_id: UUID,
        notice_document_id: UUID,
        db: AsyncSession,
        client_name: str | None = None,
        ssn_last4: str | None = None,
    ) -> NoticeResponse:
        """Generate a response letter for an IRS notice.

        Args:
            case_id: Case identifier
            notice_document_id: Notice document to respond to
            db: Database session
            client_name: Optional client name (fetched from case if not provided)
            ssn_last4: Optional SSN last 4 (required for letter)

        Returns:
            NoticeResponse with draft letter and supporting info

        Raises:
            ValueError: If document not found or analysis fails
        """
        # Get notice document
        document = await db.get(Document, notice_document_id)
        if not document:
            raise ValueError(f"Notice document not found: {notice_document_id}")

        # Get document text
        document_text = await self._get_document_text(notice_document_id, db)
        if not document_text:
            raise ValueError(f"No text found for notice: {notice_document_id}")

        # Get case context for client info
        from services.template_context import prepare_case_context
        context = await prepare_case_context(case_id, db)

        client_name = client_name or context["client_name"]
        tax_year = context["tax_year"]

        logger.info(
            "Drafting notice response",
            case_id=str(case_id),
            document_id=str(notice_document_id),
            client_name=client_name,
        )

        # Analyze the notice
        analysis = await self._analyze_notice_for_response(document_text)

        # Get notice-specific context
        notice_type = analysis.get("notice_type", "IRS Notice")
        type_context = self.NOTICE_TYPE_PROMPTS.get(notice_type, "")

        # Generate detailed response points
        response_prompt = f"""Based on this IRS notice analysis, generate detailed response points.

Notice Type: {notice_type}
{type_context}

Notice Analysis:
{orjson.dumps(analysis).decode()}

Original Notice Text:
{document_text[:3000]}...

Generate specific, professional response points for each issue. Include:
1. What the IRS is claiming
2. Our client's position
3. Supporting evidence to include

Respond with JSON only."""

        response_json = await self.model_router.generate(
            task="drafting",
            messages=[{"role": "user", "content": response_prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.2,
        )

        try:
            response_data = orjson.loads(response_json)
        except orjson.JSONDecodeError:
            response_data = analysis  # Fall back to initial analysis

        # Build response points
        response_points = []
        for issue in response_data.get("issues", []):
            response_points.append(
                NoticeResponsePoint(
                    item=issue.get("item", "Issue"),
                    response=issue.get("response", ""),
                    supporting_docs=issue.get("supporting_docs", []),
                )
            )

        # Build attachment list
        attachments = []
        for att in response_data.get("attachments_needed", []):
            attachments.append(
                AttachmentItem(
                    name=att.get("name", "Document"),
                    description=att.get("description"),
                )
            )

        # Get missing info list
        needed_info = response_data.get("missing_info", [])

        # Render the response letter template
        notice_date = response_data.get("notice_date", datetime.now().strftime("%B %d, %Y"))

        template_vars = {
            "client_name": client_name,
            "ssn_last4": ssn_last4 or "XXXX",
            "notice_type": notice_type,
            "notice_date": notice_date,
            "tax_year": tax_year,
            "response_points": [
                {"item": rp.item, "response": rp.response}
                for rp in response_points
            ],
            "attachments": [
                {"name": att.name, "description": att.description}
                for att in attachments
            ],
            "needed_info": needed_info,
            "preparer_name": "Krystal Le",
            "firm_name": "Krystal Le CPA",
            "firm_address": "123 Main Street, Suite 100\nAnytown, CA 90210",
        }

        draft_letter = self.renderer.render("notice_response", template_vars)

        # Create NoticeResponse
        notice_response = NoticeResponse(
            client_name=client_name,
            ssn_last4=ssn_last4 or "XXXX",
            notice_type=notice_type,
            notice_date=notice_date,
            tax_year=tax_year,
            response_points=response_points,
            attachments=attachments,
            needed_info=needed_info,
            preparer_name="Krystal Le",
            firm_name="Krystal Le CPA",
            firm_address="123 Main Street, Suite 100\nAnytown, CA 90210",
            draft_letter=draft_letter,
        )

        # Store as artifact
        artifact = Artifact(
            case_id=case_id,
            artifact_type="notice_response",
            title=f"{notice_type} Response - {client_name} ({tax_year})",
            content=draft_letter,
            content_format="markdown",
            is_draft=True,
            created_by="notice_agent",
        )

        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)

        logger.info(
            "Generated notice response",
            case_id=str(case_id),
            artifact_id=str(artifact.id),
            notice_type=notice_type,
            response_points_count=len(response_points),
            attachments_count=len(attachments),
        )

        return notice_response

    async def _analyze_notice_for_response(self, document_text: str) -> dict:
        """Internal analysis focused on response generation.

        Args:
            document_text: Notice text

        Returns:
            Analysis dictionary
        """
        prompt = f"""Analyze this IRS notice for response generation.

Notice text:
{document_text}

Extract:
1. Notice type (CP2000, CP501, etc.)
2. Notice date
3. Response deadline
4. Amount due (if any)
5. Specific issues raised
6. What documentation would address each issue

Respond with JSON only."""

        response = await self.model_router.generate(
            task="extraction",
            messages=[{"role": "user", "content": prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.0,
        )

        try:
            return orjson.loads(response)
        except orjson.JSONDecodeError:
            return {
                "notice_type": "IRS Notice",
                "issues": [],
                "attachments_needed": [],
                "missing_info": ["Unable to parse notice - manual review required"],
                "confidence": "LOW",
            }

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

    def get_notice_type_info(self, notice_type: str) -> dict:
        """Get information about a notice type.

        Args:
            notice_type: IRS notice type code

        Returns:
            Dictionary with description and response options
        """
        notice_info = {
            "CP2000": {
                "name": "Underreported Income",
                "severity": "medium",
                "description": "IRS received income information that doesn't match your return",
                "response_deadline_days": 30,
                "common_responses": [
                    "Income was reported on a different line",
                    "Income was reported by spouse on separate return",
                    "1099 amount is incorrect",
                    "Income is not taxable",
                ],
            },
            "CP501": {
                "name": "Balance Due Reminder",
                "severity": "low",
                "description": "First reminder that taxes are owed",
                "response_deadline_days": 21,
                "common_responses": [
                    "Pay balance in full",
                    "Request installment agreement",
                    "Dispute the balance",
                ],
            },
            "CP504": {
                "name": "Intent to Levy",
                "severity": "high",
                "description": "IRS may levy bank accounts or wages within 30 days",
                "response_deadline_days": 30,
                "common_responses": [
                    "Pay balance immediately",
                    "Set up installment agreement",
                    "Request Collection Due Process hearing",
                ],
            },
            "LT11": {
                "name": "Final Notice - Intent to Levy",
                "severity": "critical",
                "description": "Last notice before levy action",
                "response_deadline_days": 30,
                "common_responses": [
                    "Pay in full",
                    "Request Collection Due Process hearing",
                    "Apply for Currently Not Collectible status",
                ],
            },
        }

        return notice_info.get(notice_type, {
            "name": "IRS Notice",
            "severity": "medium",
            "description": "IRS notice requiring response",
            "response_deadline_days": 30,
            "common_responses": ["Review and respond to notice"],
        })
