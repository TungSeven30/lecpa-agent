"""Orchestrator agent that routes to subagents based on intent."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

import orjson
import structlog
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
