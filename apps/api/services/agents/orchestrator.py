"""Orchestrator agent that routes to subagents based on intent."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

import orjson
import structlog
from services.agents.extraction_agent import ExtractionAgent
from services.agents.intake_agent import IntakeAgent
from services.agents.notice_agent import NoticeAgent
from services.agents.qc_agent import QCAgent
from services.model_router import ModelRouter, get_model_router
from services.search import HybridSearchService, get_search_service
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.document import Citation

logger = structlog.get_logger()


@dataclass
class ChatResult:
    """Result from chat generation."""

    response: str
    citations: list[Citation]
    intent: str | None = None


class OrchestratorAgent:
    """Main orchestrator that classifies intent and routes to subagents.

    Responsibilities:
    - Classify user intent (question, drafting, extraction, notice, qc, intake)
    - Route to appropriate subagent
    - Enforce guardrails
    - Format and validate output
    """

    SYSTEM_PROMPT = """You are Krystal Le Agent, an AI assistant for a CPA firm.
You help staff with tax season workflows including:
- Answering questions about tax documents and firm procedures
- Generating missing documents emails for clients
- Drafting IRS notice responses
- Extracting data from tax forms (W-2, 1099, K-1)
- Quality control review

GUARDRAILS (MUST FOLLOW):
1. Never make tax law claims without citing a source document
2. Never fabricate numbers - all figures must come from documents or user input
3. When information is missing, always include a "NEEDED INFO" section
4. Mask SSNs - only show last 4 digits (e.g., XXX-XX-1234)

When answering questions, cite your sources using [Doc: filename, Page: X] format.
"""

    def __init__(
        self,
        model_router: ModelRouter,
        search_service: HybridSearchService,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            model_router: Router for LLM calls
            search_service: Service for document search
        """
        self.model_router = model_router
        self.search_service = search_service
        self.intake_agent = IntakeAgent(model_router)
        self.extraction_agent = ExtractionAgent(model_router)
        self.notice_agent = NoticeAgent(model_router)
        self.qc_agent = QCAgent(model_router)

    async def classify_intent(self, message: str) -> str:
        """Classify the user's intent.

        Args:
            message: User's message

        Returns:
            Intent category
        """
        prompt = f"""Classify the following user message into one of these categories:
- question: Asking about documents, procedures, or tax information
- drafting: Requesting an email, letter, or other written content
- extraction: Requesting data extraction from a document
- notice: Related to IRS notices or responses
- qc: Quality control or review request
- intake: Missing documents or organizer checklist

Message: {message}

Respond with ONLY the category name, nothing else."""

        response = await self.model_router.generate(
            task="orchestrator",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.0,
        )

        intent = response.strip().lower()
        valid_intents = {"question", "drafting", "extraction", "notice", "qc", "intake"}

        return intent if intent in valid_intents else "question"

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        db: AsyncSession,
        case_id: UUID | None = None,
        client_code: str | None = None,
    ) -> ChatResult:
        """Generate a non-streaming response.

        Args:
            messages: Conversation messages
            db: Database session for document search
            case_id: Optional case context
            client_code: Optional client context

        Returns:
            ChatResult with response and citations
        """
        if not messages:
            return ChatResult(response="No message provided.", citations=[])

        last_message = messages[-1]["content"]
        intent = await self.classify_intent(last_message)

        logger.info("Classified intent", intent=intent, case_id=case_id)

        # Route to intake subagent if needed
        if intent == "intake":
            if not case_id:
                return ChatResult(
                    response="Please select a case to generate intake artifacts.",
                    citations=[],
                    intent=intent,
                )

            # Determine which artifact to generate
            message_lower = last_message.lower()

            if "email" in message_lower:
                result = await self.intake_agent.generate_missing_docs_email(
                    case_id=case_id,
                    db=db,
                )
                response = (
                    f"I've generated a missing documents email:\n\n"
                    f"{result['preview']}\n\n"
                    f"**Artifact ID:** {result['artifact_id']}\n\n"
                    f"*The full email has been saved as a draft artifact.*"
                )

            elif "checklist" in message_lower or "organizer" in message_lower:
                result = await self.intake_agent.generate_organizer_checklist(
                    case_id=case_id,
                    db=db,
                )
                response = (
                    f"I've generated a tax organizer checklist:\n\n"
                    f"{result['preview']}\n\n"
                    f"**Artifact ID:** {result['artifact_id']}\n\n"
                    f"*The full checklist has been saved as a draft artifact.*"
                )

            else:
                # Ask which artifact type
                response = (
                    "I can help generate intake artifacts:\n\n"
                    "- **Missing documents email**: Request missing items from client\n"
                    "- **Tax organizer checklist**: Comprehensive document collection guide\n\n"
                    "Which would you like me to generate?"
                )

            return ChatResult(
                response=response,
                citations=[],
                intent=intent,
            )

        # Route to extraction subagent
        if intent == "extraction":
            if not case_id:
                return ChatResult(
                    response="Please select a case to extract document data.",
                    citations=[],
                    intent=intent,
                )

            # Try to find document reference in message
            from database.models import Document
            from sqlalchemy import select

            # Get documents for the case
            stmt = select(Document).where(Document.case_id == case_id)
            result = await db.execute(stmt)
            documents = result.scalars().all()

            if not documents:
                return ChatResult(
                    response="No documents found in this case. Please upload documents first.",
                    citations=[],
                    intent=intent,
                )

            # Determine which document to extract from
            message_lower = last_message.lower()

            # Find matching document by type or name
            target_doc = None
            for doc in documents:
                doc_tags = [t.upper() for t in (doc.tags or [])]
                if "w-2" in message_lower or "w2" in message_lower:
                    if "W2" in doc_tags:
                        target_doc = doc
                        break
                elif "1099" in message_lower:
                    if any("1099" in t for t in doc_tags):
                        target_doc = doc
                        break
                elif ("k-1" in message_lower or "k1" in message_lower) and "K1" in doc_tags:
                    target_doc = doc
                    break

            if not target_doc:
                # Default to first document or list options
                doc_list = "\n".join([f"- {d.filename} ({', '.join(d.tags or [])})" for d in documents[:10]])
                return ChatResult(
                    response=f"Which document would you like me to extract data from?\n\n{doc_list}",
                    citations=[],
                    intent=intent,
                )

            try:
                extraction_result = await self.extraction_agent.extract_document(
                    document_id=target_doc.id,
                    db=db,
                )

                # Format response
                confidence = extraction_result.overall_confidence.value.upper()
                needs_review = "Yes" if extraction_result.needs_review else "No"

                response = (
                    f"## Extraction Complete: {target_doc.filename}\n\n"
                    f"**Type:** {extraction_result.document_type}\n"
                    f"**Confidence:** {confidence}\n"
                    f"**Needs Review:** {needs_review}\n\n"
                )

                if extraction_result.w2:
                    w2 = extraction_result.w2
                    response += "### W-2 Data\n"
                    response += f"- **Employer:** {w2.employer_name or 'N/A'}\n"
                    response += f"- **Wages:** ${w2.wages:,.2f}\n" if w2.wages else "- **Wages:** N/A\n"
                    response += f"- **Federal Tax Withheld:** ${w2.federal_tax_withheld:,.2f}\n" if w2.federal_tax_withheld else "- **Federal Tax Withheld:** N/A\n"

                elif extraction_result.form_1099:
                    f1099 = extraction_result.form_1099
                    response += f"### {f1099.form_type} Data\n"
                    response += f"- **Payer:** {f1099.payer_name or 'N/A'}\n"
                    response += f"- **Amount:** ${f1099.amount:,.2f}\n" if f1099.amount else "- **Amount:** N/A\n"

                elif extraction_result.k1:
                    k1 = extraction_result.k1
                    response += "### K-1 Data\n"
                    response += f"- **Partnership:** {k1.partnership_name or 'N/A'}\n"
                    response += f"- **Ordinary Income:** ${k1.ordinary_income:,.2f}\n" if k1.ordinary_income else "- **Ordinary Income:** N/A\n"

                if extraction_result.anomalies:
                    response += "\n### ⚠️ Anomalies Detected\n"
                    for anomaly in extraction_result.anomalies:
                        response += f"- {anomaly}\n"

                response += "\n*Extraction result has been saved as an artifact.*"

            except Exception as e:
                logger.error("Extraction failed", error=str(e), document_id=str(target_doc.id))
                response = f"Failed to extract data from {target_doc.filename}: {str(e)}"

            return ChatResult(
                response=response,
                citations=[],
                intent=intent,
            )

        # Route to notice subagent
        if intent == "notice":
            if not case_id:
                return ChatResult(
                    response="Please select a case to draft a notice response.",
                    citations=[],
                    intent=intent,
                )

            # Find IRS notice documents
            from database.models import Document
            from sqlalchemy import select

            stmt = select(Document).where(Document.case_id == case_id)
            result = await db.execute(stmt)
            documents = result.scalars().all()

            notice_docs = [
                d for d in documents
                if "IRS_NOTICE" in (d.tags or []) or "notice" in d.filename.lower()
            ]

            if not notice_docs:
                return ChatResult(
                    response="No IRS notice documents found in this case. Please upload the notice first.",
                    citations=[],
                    intent=intent,
                )

            # Use first notice document
            notice_doc = notice_docs[0]

            try:
                notice_response = await self.notice_agent.draft_notice_response(
                    case_id=case_id,
                    notice_document_id=notice_doc.id,
                    db=db,
                )

                response = (
                    f"## IRS Notice Response Draft\n\n"
                    f"**Notice Type:** {notice_response.notice_type}\n"
                    f"**Tax Year:** {notice_response.tax_year}\n\n"
                    f"### Response Preview\n\n"
                    f"{notice_response.draft_letter[:1000]}...\n\n"
                )

                if notice_response.needed_info:
                    response += "### ⚠️ Information Needed\n"
                    for info in notice_response.needed_info:
                        response += f"- {info}\n"

                if notice_response.attachments:
                    response += "\n### Attachments to Include\n"
                    for att in notice_response.attachments:
                        response += f"- {att.name}"
                        if att.description:
                            response += f" - {att.description}"
                        response += "\n"

                response += "\n*The full response letter has been saved as a draft artifact.*"

            except Exception as e:
                logger.error("Notice response failed", error=str(e))
                response = f"Failed to draft notice response: {str(e)}"

            return ChatResult(
                response=response,
                citations=[],
                intent=intent,
            )

        # Route to QC subagent
        if intent == "qc":
            if not case_id:
                return ChatResult(
                    response="Please select a case to run QC review.",
                    citations=[],
                    intent=intent,
                )

            try:
                qc_report = await self.qc_agent.generate_qc_memo(
                    case_id=case_id,
                    db=db,
                )

                status_emoji = "✅" if qc_report.pass_status else "❌"
                status_text = "PASS" if qc_report.pass_status else "NEEDS ATTENTION"

                response = (
                    f"## QC Review Complete {status_emoji}\n\n"
                    f"**Client:** {qc_report.client_name}\n"
                    f"**Tax Year:** {qc_report.tax_year}\n"
                    f"**Status:** {status_text}\n\n"
                    f"### Summary\n{qc_report.summary}\n\n"
                )

                if qc_report.findings:
                    response += f"### Findings ({len(qc_report.findings)})\n"
                    for finding in qc_report.findings[:5]:  # Show first 5
                        severity_icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(finding.severity, "⚪")
                        response += f"{severity_icon} **{finding.category.title()}:** {finding.description}\n"
                    if len(qc_report.findings) > 5:
                        response += f"\n*...and {len(qc_report.findings) - 5} more findings*\n"

                if qc_report.missing_documents:
                    response += "\n### Missing Documents\n"
                    for doc in qc_report.missing_documents[:5]:
                        response += f"- {doc}\n"

                response += "\n*QC memo has been saved as an artifact.*"

            except Exception as e:
                logger.error("QC review failed", error=str(e))
                response = f"Failed to complete QC review: {str(e)}"

            return ChatResult(
                response=response,
                citations=[],
                intent=intent,
            )

        # Search for relevant context
        citations: list[Citation] = []
        context = ""

        if intent in {"question", "notice", "qc"}:
            # Search for relevant documents
            citations = await self.search_service.search(
                query=last_message,
                db=db,
                case_id=case_id,
                client_code=client_code,
                top_k=5,
            )

            if citations:
                context_parts = []
                for c in citations:
                    page_ref = (
                        f"Page {c.page_start}"
                        if c.page_start == c.page_end
                        else f"Pages {c.page_start}-{c.page_end}"
                    )
                    context_parts.append(
                        f"[Doc: {c.document_filename}, {page_ref}]\n{c.snippet}"
                    )
                context = "\n\n---\n\n".join(context_parts)

                logger.info(
                    "Found relevant documents",
                    citation_count=len(citations),
                    case_id=case_id,
                )

        # Build messages with system prompt and context
        full_messages = [{"role": "user", "content": msg["content"]} for msg in messages]

        if context:
            # Prepend context to the last message
            full_messages[-1]["content"] = f"""Context from documents:
{context}

User question: {full_messages[-1]['content']}"""

        response = await self.model_router.generate(
            task="orchestrator",
            messages=full_messages,
            system=self.SYSTEM_PROMPT,
        )

        return ChatResult(
            response=response,
            citations=citations,
            intent=intent,
        )

    async def stream_response(
        self,
        messages: list[dict[str, str]],
        db: AsyncSession,
        case_id: UUID | None = None,
        client_code: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a response using Server-Sent Events format.

        Args:
            messages: Conversation messages
            db: Database session for document search
            case_id: Optional case context
            client_code: Optional client context

        Yields:
            SSE-formatted response chunks
        """
        if not messages:
            yield "data: No message provided.\n\n"
            return

        last_message = messages[-1]["content"]
        intent = await self.classify_intent(last_message)

        # Send intent as first event
        yield f"event: intent\ndata: {intent}\n\n"

        # Search for relevant context
        citations: list[Citation] = []
        context = ""

        if intent in {"question", "notice", "qc"}:
            citations = await self.search_service.search(
                query=last_message,
                db=db,
                case_id=case_id,
                client_code=client_code,
                top_k=5,
            )

            if citations:
                context_parts = []
                for c in citations:
                    page_ref = (
                        f"Page {c.page_start}"
                        if c.page_start == c.page_end
                        else f"Pages {c.page_start}-{c.page_end}"
                    )
                    context_parts.append(
                        f"[Doc: {c.document_filename}, {page_ref}]\n{c.snippet}"
                    )
                context = "\n\n---\n\n".join(context_parts)

                # Send citations as event before response
                citations_data = [c.model_dump() for c in citations]
                yield f"event: citations\ndata: {orjson.dumps(citations_data).decode()}\n\n"

        # Build messages
        full_messages = [{"role": "user", "content": msg["content"]} for msg in messages]

        if context:
            full_messages[-1]["content"] = f"""Context from documents:
{context}

User question: {full_messages[-1]['content']}"""

        # Stream the response
        async for chunk in self.model_router.stream(
            task="orchestrator",
            messages=full_messages,
            system=self.SYSTEM_PROMPT,
        ):
            # Escape newlines for SSE
            escaped = chunk.replace("\n", "\\n")
            yield f"data: {escaped}\n\n"

        # Send done event
        yield "event: done\ndata: complete\n\n"


@lru_cache
def get_orchestrator() -> OrchestratorAgent:
    """Get cached orchestrator instance."""
    return OrchestratorAgent(
        model_router=get_model_router(),
        search_service=get_search_service(),
    )
