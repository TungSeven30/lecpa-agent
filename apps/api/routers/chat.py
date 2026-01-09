"""Chat router with streaming responses."""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_async_db
from services.agents.orchestrator import OrchestratorAgent, get_orchestrator
from shared.models.document import Citation

router = APIRouter()


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = Field(pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    """Chat request parameters."""

    messages: list[ChatMessage]
    case_id: UUID | None = None
    client_code: str | None = None
    stream: bool = True


class ChatResponse(BaseModel):
    """Non-streaming chat response."""

    response: str
    citations: list[Citation] = Field(default_factory=list)
    intent: str | None = None


@router.post("")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_async_db),
    orchestrator: OrchestratorAgent = Depends(get_orchestrator),
) -> StreamingResponse | ChatResponse:
    """Chat with the AI assistant.

    Supports both streaming (SSE) and non-streaming responses.
    The orchestrator routes to appropriate subagents based on intent.
    """
    if request.stream:
        return StreamingResponse(
            orchestrator.stream_response(
                messages=request.messages,
                case_id=request.case_id,
                client_code=request.client_code,
            ),
            media_type="text/event-stream",
        )

    # Non-streaming response
    result = await orchestrator.generate_response(
        messages=request.messages,
        case_id=request.case_id,
        client_code=request.client_code,
    )

    return ChatResponse(
        response=result.response,
        citations=result.citations,
        intent=result.intent,
    )
