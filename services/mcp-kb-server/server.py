"""MCP server for knowledge base operations (search, templates).

Provides tools for template discovery, rendering, and document search.
Used by agents to access firm knowledge and generate artifacts.
"""

import asyncio
import sys
from pathlib import Path

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

# Add workspace root to path for imports
workspace_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workspace_root))

from apps.api.services.template_renderer import get_template_renderer

logger = structlog.get_logger()

# Initialize MCP server
server = Server("mcp-kb-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools.

    Returns:
        List of tool definitions for template operations
    """
    return [
        Tool(
            name="list_templates",
            description=(
                "List available templates with optional filtering by type or category. "
                "Returns template metadata including required/optional variables."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Filter by artifact type",
                        "enum": [
                            "missing_docs_email",
                            "organizer_checklist",
                            "notice_response",
                            "qc_memo",
                            "extraction_result",
                        ],
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category",
                        "enum": [
                            "communication",
                            "intake",
                            "correspondence",
                            "internal",
                            "extraction",
                        ],
                    },
                },
            },
        ),
        Tool(
            name="render_template",
            description=(
                "Render a template with provided variables. "
                "Returns rendered content as markdown or JSON. "
                "Validates required variables by default."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "Template identifier (e.g., missing_docs_email)",
                    },
                    "variables": {
                        "type": "object",
                        "description": "Template variables as JSON object",
                    },
                    "validate": {
                        "type": "boolean",
                        "description": "Whether to validate variables (default: true)",
                        "default": True,
                    },
                },
                "required": ["template_id", "variables"],
            },
        ),
        Tool(
            name="get_template_schema",
            description=(
                "Get template metadata including required/optional variables schema. "
                "Use this to discover what variables a template needs before rendering."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "Template identifier",
                    },
                },
                "required": ["template_id"],
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
    renderer = get_template_renderer()

    if name == "list_templates":
        # List templates with optional filters
        templates = renderer.list_templates(
            template_type=arguments.get("type"),
            category=arguments.get("category"),
        )

        result = [
            {
                "id": t.id,
                "name": t.name,
                "type": t.type,
                "description": t.description,
                "category": t.category,
                "output_format": t.output_format,
            }
            for t in templates
        ]

        logger.info(
            "Listed templates",
            count=len(result),
            filter_type=arguments.get("type"),
            filter_category=arguments.get("category"),
        )

        return CallToolResult(
            content=[TextContent(type="text", text=str(result))],
        )

    elif name == "render_template":
        # Render template with variables
        template_id = arguments["template_id"]
        variables = arguments["variables"]
        validate = arguments.get("validate", True)

        try:
            rendered = renderer.render(template_id, variables, validate=validate)

            logger.info(
                "Rendered template",
                template_id=template_id,
                output_length=len(rendered),
            )

            return CallToolResult(
                content=[TextContent(type="text", text=rendered)],
            )

        except ValueError as e:
            logger.error(
                "Template rendering failed",
                template_id=template_id,
                error=str(e),
            )
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {e}")],
                isError=True,
            )

    elif name == "get_template_schema":
        # Get template metadata/schema
        template_id = arguments["template_id"]
        metadata = renderer.get_template_metadata(template_id)

        if not metadata:
            return CallToolResult(
                content=[
                    TextContent(type="text", text=f"Template not found: {template_id}")
                ],
                isError=True,
            )

        schema = {
            "id": metadata.id,
            "name": metadata.name,
            "description": metadata.description,
            "type": metadata.type,
            "category": metadata.category,
            "variables": metadata.variables,
            "output_format": metadata.output_format,
            "filename": metadata.filename,
        }

        logger.info("Retrieved template schema", template_id=template_id)

        return CallToolResult(
            content=[TextContent(type="text", text=str(schema))],
        )

    return CallToolResult(
        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
        isError=True,
    )


async def main() -> None:
    """Run the MCP server."""
    logger.info("Starting MCP KB server")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
