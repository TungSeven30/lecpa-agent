"""MCP server for case management operations.

Provides tools for artifact storage and case information retrieval.
Used by agents to save generated artifacts and access case context.
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

import orjson
import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool
from sqlalchemy import select

# Add workspace root to path
workspace_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workspace_root))

from apps.api.database.models import Artifact, Case, Document
from apps.api.database.session import get_async_db

logger = structlog.get_logger()

# Initialize MCP server
server = Server("mcp-case-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools.

    Returns:
        List of tool definitions for case/artifact operations
    """
    return [
        Tool(
            name="write_artifact",
            description=(
                "Save a generated artifact to a case. "
                "Creates a new artifact record with draft status by default. "
                "Returns the artifact ID."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "string",
                        "description": "Case UUID",
                    },
                    "artifact_type": {
                        "type": "string",
                        "description": "Type of artifact",
                        "enum": [
                            "missing_docs_email",
                            "organizer_checklist",
                            "notice_response",
                            "qc_memo",
                            "extraction_result",
                            "summary",
                            "custom",
                        ],
                    },
                    "title": {
                        "type": "string",
                        "description": "Artifact title (user-facing)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Artifact content (rendered template or generated text)",
                    },
                    "content_format": {
                        "type": "string",
                        "description": "Content format",
                        "enum": ["markdown", "json", "html", "text"],
                        "default": "markdown",
                    },
                    "is_draft": {
                        "type": "boolean",
                        "description": "Whether artifact is a draft (default: true)",
                        "default": True,
                    },
                },
                "required": ["case_id", "artifact_type", "title", "content"],
            },
        ),
        Tool(
            name="get_case_summary",
            description=(
                "Get case summary with documents and artifacts count. "
                "Returns case metadata, document list, and artifact count."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "case_id": {
                        "type": "string",
                        "description": "Case UUID",
                    },
                },
                "required": ["case_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    """Handle tool calls.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        Tool execution result
    """

    if name == "write_artifact":
        async for db in get_async_db():
            try:
                case_id = UUID(arguments["case_id"])

                # Verify case exists
                result = await db.execute(select(Case).where(Case.id == case_id))
                if not result.scalar_one_or_none():
                    return CallToolResult(
                        content=[
                            TextContent(type="text", text=f"Case not found: {case_id}")
                        ],
                        isError=True,
                    )

                # Create artifact
                artifact = Artifact(
                    case_id=case_id,
                    artifact_type=arguments["artifact_type"],
                    title=arguments["title"],
                    content=arguments["content"],
                    content_format=arguments.get("content_format", "markdown"),
                    is_draft=arguments.get("is_draft", True),
                    created_by="agent",
                )

                db.add(artifact)
                await db.commit()
                await db.refresh(artifact)

                logger.info(
                    "Artifact created",
                    artifact_id=str(artifact.id),
                    case_id=str(case_id),
                    type=artifact.artifact_type,
                )

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Artifact created: {artifact.id}",
                        )
                    ],
                )

            except ValueError as e:
                logger.error("Invalid case ID", error=str(e))
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Invalid UUID: {e}")],
                    isError=True,
                )
            except Exception as e:
                logger.error("Failed to write artifact", error=str(e))
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {e}")],
                    isError=True,
                )

    elif name == "get_case_summary":
        async for db in get_async_db():
            try:
                case_id = UUID(arguments["case_id"])

                # Fetch case
                result = await db.execute(select(Case).where(Case.id == case_id))
                case = result.scalar_one_or_none()

                if not case:
                    return CallToolResult(
                        content=[
                            TextContent(type="text", text=f"Case not found: {case_id}")
                        ],
                        isError=True,
                    )

                # Count documents and artifacts
                docs_result = await db.execute(
                    select(Document).where(Document.case_id == case_id)
                )
                documents = docs_result.scalars().all()

                artifacts_result = await db.execute(
                    select(Artifact).where(Artifact.case_id == case_id)
                )
                artifacts = artifacts_result.scalars().all()

                summary = {
                    "case_id": str(case.id),
                    "client_id": str(case.client_id),
                    "tax_year": case.tax_year,
                    "case_type": case.case_type,
                    "status": case.status,
                    "document_count": len(documents),
                    "artifact_count": len(artifacts),
                    "documents": [
                        {
                            "filename": doc.filename,
                            "status": doc.processing_status,
                            "tags": doc.tags,
                        }
                        for doc in documents
                    ],
                }

                logger.info(
                    "Retrieved case summary",
                    case_id=str(case_id),
                    document_count=len(documents),
                    artifact_count=len(artifacts),
                )

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=orjson.dumps(summary).decode(),
                        )
                    ],
                )

            except ValueError as e:
                logger.error("Invalid case ID", error=str(e))
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Invalid UUID: {e}")],
                    isError=True,
                )
            except Exception as e:
                logger.error("Failed to get case summary", error=str(e))
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {e}")],
                    isError=True,
                )

    return CallToolResult(
        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
        isError=True,
    )


async def main() -> None:
    """Run the MCP server."""
    logger.info("Starting MCP case server")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
