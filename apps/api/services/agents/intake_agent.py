"""Intake and missing documents subagent.

First production subagent serving as reference implementation for the agent pattern.
Analyzes case documents to identify missing items and generates client-facing artifacts.
"""

from datetime import datetime, timedelta
from uuid import UUID

import orjson
import structlog
from database.models import Artifact
from services.model_router import ModelRouter
from services.template_context import prepare_case_context
from services.template_renderer import get_template_renderer
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class IntakeAgent:
    """Subagent for intake and missing documents workflows.

    Responsibilities:
    - Analyze case documents to identify missing tax items
    - Generate comprehensive missing documents checklists
    - Draft professional client communication emails
    - Save generated artifacts to database

    Example:
        agent = IntakeAgent(model_router)
        result = await agent.generate_missing_docs_email(case_id, db)
        # result = {"artifact_id": "...", "preview": "..."}
    """

    SYSTEM_PROMPT = """You are an intake specialist for a CPA firm assisting with tax preparation.

Your responsibilities:
1. Review case documents to identify missing tax documents
2. Generate comprehensive checklists for document collection
3. Draft professional client communication emails
4. Always be specific about WHY each document is needed

When generating missing docs lists:
- Be thorough but not overwhelming (5-10 items maximum)
- Prioritize by importance (required vs. helpful)
- Explain the purpose of each document clearly
- Consider the case type (1040 individual vs. business return)
- Only list items that are actually missing (don't repeat docs already uploaded)

For individual 1040 returns, common docs include:
- W-2s (wage income)
- 1099s (interest, dividends, self-employment, misc income)
- 1098 (mortgage interest, student loan interest)
- Prior year tax return
- HSA contributions
- Childcare expenses
- Education expenses (1098-T, receipts)

For business returns, common docs include:
- Business bank statements
- P&L statement
- Balance sheet
- Depreciation schedule
- Vehicle mileage logs

Output your analysis as JSON in this exact format:
{
  "missing_items": [
    {"name": "Document name", "description": "Why it's needed"},
    ...
  ],
  "deadline_days": 14
}

Respond with ONLY the JSON, no additional text."""

    def __init__(self, model_router: ModelRouter) -> None:
        """Initialize the intake agent.

        Args:
            model_router: Router for LLM calls
        """
        self.model_router = model_router
        self.renderer = get_template_renderer()

    async def generate_missing_docs_email(
        self,
        case_id: UUID,
        db: AsyncSession,
        custom_items: list[dict[str, str]] | None = None,
    ) -> dict[str, str]:
        """Generate missing documents email for a case.

        Analyzes the case's existing documents using Claude, identifies
        missing items, renders the email template, and saves as artifact.

        Args:
            case_id: Case identifier
            db: Database session
            custom_items: Optional custom missing items (skips LLM analysis)

        Returns:
            Dictionary with:
            - artifact_id: UUID of created artifact
            - preview: First 500 chars of generated email

        Raises:
            ValueError: If case not found or template rendering fails
        """
        # Prepare context from case
        context = await prepare_case_context(case_id, db)

        # If no custom items provided, analyze documents with LLM
        if not custom_items:
            analysis_prompt = self._build_analysis_prompt(context)

            logger.info(
                "Analyzing case for missing documents",
                case_id=str(case_id),
                existing_docs=context["document_count"],
            )

            # Get LLM analysis
            analysis_json = await self.model_router.generate(
                task="drafting",
                messages=[{"role": "user", "content": analysis_prompt}],
                system=self.SYSTEM_PROMPT,
                temperature=0.2,
            )

            # Parse JSON response
            try:
                analysis = orjson.loads(analysis_json)
                missing_items = analysis.get("missing_items", [])
                deadline_days = analysis.get("deadline_days", 14)
            except orjson.JSONDecodeError as e:
                logger.error(
                    "Failed to parse LLM analysis JSON",
                    error=str(e),
                    response=analysis_json,
                )
                # Fallback to generic message
                missing_items = [
                    {
                        "name": "Required tax documents",
                        "description": "Please provide any missing documents for your tax return",
                    }
                ]
                deadline_days = 14
        else:
            missing_items = custom_items
            deadline_days = 14

        # Calculate deadline
        deadline_date = datetime.now() + timedelta(days=deadline_days)
        deadline_str = deadline_date.strftime("%B %d, %Y")

        # Render template
        template_vars = {
            "client_name": context["client_name"],
            "tax_year": context["tax_year"],
            "firm_name": "Krystal Le CPA",
            "preparer_name": "Krystal Le",
            "missing_items": missing_items,
            "deadline": deadline_str,
        }

        content = self.renderer.render("missing_docs_email", template_vars)

        # Save artifact
        artifact = Artifact(
            case_id=case_id,
            artifact_type="missing_docs_email",
            title=f"{context['tax_year']} Tax Return - Documents Needed",
            content=content,
            content_format="markdown",
            is_draft=True,
            created_by="agent",
        )

        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)

        logger.info(
            "Generated missing docs email",
            case_id=str(case_id),
            artifact_id=str(artifact.id),
            items_count=len(missing_items),
        )

        return {
            "artifact_id": str(artifact.id),
            "preview": content[:500] + "..." if len(content) > 500 else content,
        }

    async def generate_organizer_checklist(
        self,
        case_id: UUID,
        db: AsyncSession,
    ) -> dict[str, str]:
        """Generate tax organizer checklist for a case.

        Creates a comprehensive document collection checklist based on
        the case type (individual vs. business return).

        Args:
            case_id: Case identifier
            db: Database session

        Returns:
            Dictionary with artifact_id and preview

        Raises:
            ValueError: If case not found
        """
        context = await prepare_case_context(case_id, db)

        # Determine return type from case
        case_type_lower = context["case_type"].lower()
        if "business" in case_type_lower or "corp" in case_type_lower:
            return_type = "business"
        else:
            return_type = "individual"

        logger.info(
            "Generating organizer checklist",
            case_id=str(case_id),
            return_type=return_type,
        )

        template_vars = {
            "client_name": context["client_name"],
            "tax_year": context["tax_year"],
            "return_type": return_type,
            "firm_name": "Krystal Le CPA",
            # Optional: could add custom items from LLM analysis
        }

        content = self.renderer.render("organizer_checklist", template_vars)

        # Save artifact
        artifact = Artifact(
            case_id=case_id,
            artifact_type="organizer_checklist",
            title=f"{context['tax_year']} Tax Organizer - {context['client_name']}",
            content=content,
            content_format="markdown",
            is_draft=True,
            created_by="agent",
        )

        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)

        logger.info(
            "Generated organizer checklist",
            case_id=str(case_id),
            artifact_id=str(artifact.id),
        )

        return {
            "artifact_id": str(artifact.id),
            "preview": content[:500] + "..." if len(content) > 500 else content,
        }

    def _build_analysis_prompt(self, context: dict) -> str:
        """Build LLM prompt for missing documents analysis.

        Args:
            context: Case context from prepare_case_context()

        Returns:
            Formatted prompt string
        """
        docs_list = ", ".join(
            [f"{d['filename']} ({d['type']})" for d in context["documents"]]
        )

        return f"""Analyze this tax case and identify missing documents.

Case Context:
- Client: {context['client_name']}
- Tax Year: {context['tax_year']}
- Case Type: {context['case_type']}
- Existing Documents ({context['document_count']}): {docs_list if docs_list else 'None uploaded yet'}

What documents are typically needed for a {context['case_type']} that are missing?
List 5-10 items with brief descriptions of why they're needed.

Respond with JSON only."""
