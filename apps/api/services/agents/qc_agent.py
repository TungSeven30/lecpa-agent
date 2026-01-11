"""Quality Control (QC) subagent.

Performs quality control review of tax cases, checking for completeness,
accuracy, and consistency across documents.
"""

from datetime import datetime
from uuid import UUID

import orjson
import structlog
from database.models import Artifact, Case
from services.model_router import ModelRouter
from services.template_renderer import get_template_renderer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.agent_outputs import (
    QCFinding,
    QCReport,
)

logger = structlog.get_logger()


class QCAgent:
    """Subagent for quality control review of tax cases.

    Responsibilities:
    - Run firm checklists against case documents
    - Cross-reference data across multiple documents
    - Flag anomalies and inconsistencies
    - Generate QC memos for review

    Example:
        agent = QCAgent(model_router)
        report = await agent.generate_qc_memo(case_id, db)
        # report.findings contains all issues found
    """

    SYSTEM_PROMPT = """You are a Quality Control reviewer for a CPA firm.

Your responsibilities:
1. Review tax case documents for completeness
2. Cross-check data consistency across documents (W-2s, 1099s, K-1s)
3. Identify missing required documents
4. Flag mathematical or logical anomalies
5. Verify tax return accuracy

QC Checklist Categories:
1. **Completeness**: Are all required documents present?
2. **Accuracy**: Do numbers match across documents and return?
3. **Consistency**: Are there any conflicting data points?
4. **Reasonableness**: Do the numbers make sense (no obvious errors)?
5. **Compliance**: Are all required forms included?

Common Issues to Check:
- W-2 wages should match across all W-2s
- Total income on return should equal sum of all income documents
- State wages typically equal federal wages (unless multi-state)
- Social Security tax should be ~6.2% of wages (up to limit)
- Medicare tax should be ~1.45% of wages
- Withholding amounts should be reasonable relative to income

Output your findings as JSON in this exact format:
{
  "findings": [
    {
      "severity": "error/warning/info",
      "category": "completeness/accuracy/consistency/reasonableness/compliance",
      "description": "What the issue is",
      "location": "Where the issue was found (document/field)",
      "recommendation": "How to resolve"
    }
  ],
  "missing_documents": ["List of missing required documents"],
  "data_anomalies": ["List of data inconsistencies found"],
  "pass_status": true/false,
  "summary": "Overall assessment"
}

Be thorough but practical. Flag real issues, not theoretical concerns.
Respond with ONLY the JSON object."""

    INDIVIDUAL_CHECKLIST = """
Individual (1040) QC Checklist:

Required Documents:
- [ ] All W-2s for employment income
- [ ] 1099-INT for interest income > $10
- [ ] 1099-DIV for dividend income
- [ ] 1099-B for investment sales
- [ ] 1099-R for retirement distributions
- [ ] 1099-G for state tax refunds
- [ ] Prior year tax return for comparison

Income Verification:
- [ ] Total wages match sum of W-2s
- [ ] Interest income matches 1099-INTs
- [ ] Dividend income matches 1099-DIVs
- [ ] Schedule D required if capital gains/losses

Deductions/Credits:
- [ ] Itemized vs Standard deduction evaluated
- [ ] Child tax credit eligibility verified
- [ ] Education credits properly claimed

State Requirements:
- [ ] State return prepared for each state with income
- [ ] State withholding allocated correctly
"""

    BUSINESS_CHECKLIST = """
Business Return QC Checklist:

Required Documents:
- [ ] Year-end financial statements
- [ ] Bank statements (all accounts)
- [ ] K-1s for all partners/shareholders
- [ ] Depreciation schedule
- [ ] Prior year return for comparison

Income Verification:
- [ ] Gross receipts reconcile to bank deposits
- [ ] Cost of goods sold properly calculated
- [ ] K-1 allocations equal total income

Deductions:
- [ ] All deductions properly substantiated
- [ ] Meals deduction limited to 50%
- [ ] Vehicle expenses properly documented
- [ ] Home office deduction eligibility

Compliance:
- [ ] Estimated tax payments tracked
- [ ] Required forms included (1099s issued to contractors)
"""

    def __init__(self, model_router: ModelRouter) -> None:
        """Initialize the QC agent.

        Args:
            model_router: Router for LLM calls
        """
        self.model_router = model_router
        self.renderer = get_template_renderer()

    async def generate_qc_memo(
        self,
        case_id: UUID,
        db: AsyncSession,
        reviewer_name: str = "Krystal Le",
    ) -> QCReport:
        """Generate a QC review memo for a case.

        Performs comprehensive quality control review and generates
        a memo documenting findings.

        Args:
            case_id: Case to review
            db: Database session
            reviewer_name: Name of reviewer for memo

        Returns:
            QCReport with findings and memo

        Raises:
            ValueError: If case not found
        """
        # Get case
        case = await db.get(Case, case_id)
        if not case:
            raise ValueError(f"Case not found: {case_id}")

        # Get case context
        from services.template_context import prepare_case_context
        context = await prepare_case_context(case_id, db)

        client_name = context["client_name"]
        tax_year = context["tax_year"]
        case_type = context["case_type"]

        logger.info(
            "Generating QC memo",
            case_id=str(case_id),
            client_name=client_name,
            tax_year=tax_year,
        )

        # Get all extraction artifacts for this case
        extraction_data = await self._get_extraction_data(case_id, db)

        # Determine checklist based on case type
        if "business" in case_type.lower() or "corp" in case_type.lower():
            checklist = self.BUSINESS_CHECKLIST
        else:
            checklist = self.INDIVIDUAL_CHECKLIST

        # Build QC review prompt
        documents_summary = self._build_documents_summary(context["documents"])
        extraction_summary = self._build_extraction_summary(extraction_data)

        prompt = f"""Perform a comprehensive QC review of this tax case.

Case Information:
- Client: {client_name}
- Tax Year: {tax_year}
- Case Type: {case_type}

Documents on File:
{documents_summary}

Extraction Data (from processed documents):
{extraction_summary}

Applicable Checklist:
{checklist}

Review the case against the checklist. Identify:
1. Missing required documents
2. Data inconsistencies
3. Calculation errors
4. Compliance issues

Be thorough but practical. Only flag real issues.
Respond with JSON only."""

        response = await self.model_router.generate(
            task="qc",
            messages=[{"role": "user", "content": prompt}],
            system=self.SYSTEM_PROMPT,
            temperature=0.1,
        )

        try:
            qc_data = orjson.loads(response)
        except orjson.JSONDecodeError as e:
            logger.error("Failed to parse QC review JSON", error=str(e))
            qc_data = {
                "findings": [
                    {
                        "severity": "error",
                        "category": "compliance",
                        "description": "QC review failed to complete",
                        "recommendation": "Manual review required",
                    }
                ],
                "missing_documents": [],
                "data_anomalies": [],
                "pass_status": False,
                "summary": "QC review encountered an error",
            }

        # Run additional automated checks
        automated_findings = self._run_automated_checks(extraction_data, context)
        qc_data["findings"].extend(automated_findings)

        # Build QCFinding objects
        findings = []
        for f in qc_data.get("findings", []):
            findings.append(
                QCFinding(
                    severity=f.get("severity", "info"),
                    category=f.get("category", "other"),
                    description=f.get("description", ""),
                    location=f.get("location"),
                    recommendation=f.get("recommendation"),
                )
            )

        # Determine pass status
        has_errors = any(f.severity == "error" for f in findings)
        pass_status = not has_errors and qc_data.get("pass_status", True)

        # Create QC report
        qc_report = QCReport(
            case_id=case_id,
            client_name=client_name,
            tax_year=tax_year,
            checked_at=datetime.now().isoformat(),
            findings=findings,
            missing_documents=qc_data.get("missing_documents", []),
            data_anomalies=qc_data.get("data_anomalies", []),
            pass_status=pass_status,
            summary=qc_data.get("summary", "QC review complete"),
        )

        # Render QC memo template
        template_vars = {
            "client_name": client_name,
            "tax_year": tax_year,
            "reviewer_name": reviewer_name,
            "review_date": datetime.now().strftime("%B %d, %Y"),
            "findings": [
                {
                    "category": f.category.title(),
                    "issue": f.description,
                    "recommendation": f.recommendation or "Review and address",
                    "priority": f.severity.title(),
                }
                for f in findings
            ],
            "follow_up_items": [
                f.description for f in findings if f.severity in ("error", "warning")
            ],
        }

        memo_content = self.renderer.render("qc_memo", template_vars)

        # Store as artifact
        artifact = Artifact(
            case_id=case_id,
            artifact_type="qc_memo",
            title=f"QC Review - {client_name} ({tax_year})",
            content=memo_content,
            content_format="markdown",
            is_draft=True,
            created_by="qc_agent",
        )

        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)

        logger.info(
            "Generated QC memo",
            case_id=str(case_id),
            artifact_id=str(artifact.id),
            findings_count=len(findings),
            pass_status=pass_status,
        )

        return qc_report

    async def run_checklist(
        self,
        case_id: UUID,
        checklist_type: str,
        db: AsyncSession,
    ) -> dict:
        """Run a specific checklist against a case.

        Args:
            case_id: Case to check
            checklist_type: Type of checklist (individual, business, etc.)
            db: Database session

        Returns:
            Dictionary with checklist results
        """
        from services.template_context import prepare_case_context
        context = await prepare_case_context(case_id, db)

        if checklist_type == "individual":
            checklist = self.INDIVIDUAL_CHECKLIST
        elif checklist_type == "business":
            checklist = self.BUSINESS_CHECKLIST
        else:
            raise ValueError(f"Unknown checklist type: {checklist_type}")

        documents_summary = self._build_documents_summary(context["documents"])

        prompt = f"""Check this case against the {checklist_type} checklist.

Documents on File:
{documents_summary}

Checklist:
{checklist}

For each checklist item, determine if it:
- PASS: Item is satisfied
- FAIL: Item is not satisfied
- N/A: Item doesn't apply to this case

Return JSON with:
{{
  "checklist_items": [
    {{"item": "description", "status": "PASS/FAIL/N/A", "notes": "explanation"}}
  ],
  "overall_status": "PASS/FAIL",
  "critical_failures": ["list of FAIL items that are critical"]
}}"""

        response = await self.model_router.generate(
            task="qc",
            messages=[{"role": "user", "content": prompt}],
            system="You are a QC checklist reviewer. Evaluate each item objectively.",
            temperature=0.0,
        )

        try:
            return orjson.loads(response)
        except orjson.JSONDecodeError:
            return {
                "checklist_items": [],
                "overall_status": "ERROR",
                "critical_failures": ["Failed to complete checklist review"],
            }

    async def _get_extraction_data(
        self,
        case_id: UUID,
        db: AsyncSession,
    ) -> list[dict]:
        """Get all extraction artifacts for a case.

        Args:
            case_id: Case identifier
            db: Database session

        Returns:
            List of extraction data dictionaries
        """
        stmt = (
            select(Artifact)
            .where(Artifact.case_id == case_id)
            .where(Artifact.artifact_type == "extraction_result")
        )
        result = await db.execute(stmt)
        artifacts = result.scalars().all()

        extractions = []
        for artifact in artifacts:
            # Try to parse the artifact content for structured data
            # The content is markdown, so we extract key values
            extractions.append({
                "title": artifact.title,
                "content": artifact.content,
                "created_at": artifact.created_at.isoformat(),
            })

        return extractions

    def _build_documents_summary(self, documents: list[dict]) -> str:
        """Build a summary of documents for the prompt.

        Args:
            documents: List of document info dicts

        Returns:
            Formatted string summary
        """
        if not documents:
            return "No documents on file."

        lines = []
        for doc in documents:
            tags = ", ".join(doc.get("tags", [])) or "untagged"
            status = doc.get("processing_status", "unknown")
            lines.append(f"- {doc['filename']} ({tags}) - Status: {status}")

        return "\n".join(lines)

    def _build_extraction_summary(self, extractions: list[dict]) -> str:
        """Build a summary of extraction data.

        Args:
            extractions: List of extraction data

        Returns:
            Formatted string summary
        """
        if not extractions:
            return "No extraction data available."

        lines = []
        for ext in extractions:
            lines.append(f"### {ext['title']}")
            # Include first 500 chars of content
            content_preview = ext["content"][:500]
            lines.append(content_preview)
            lines.append("")

        return "\n".join(lines)

    def _run_automated_checks(
        self,
        _extractions: list[dict],
        context: dict,
    ) -> list[dict]:
        """Run automated validation checks on extracted data.

        Args:
            _extractions: Extraction data (reserved for cross-referencing)
            context: Case context

        Returns:
            List of findings from automated checks
        """
        findings = []

        # Check for minimum required documents based on case type
        doc_types = [d.get("type", "").upper() for d in context.get("documents", [])]

        # Individual return checks
        is_individual_return = context["case_type"].lower() in ("tax_return", "1040")
        has_docs_but_no_w2 = not any("W2" in t for t in doc_types) and context["document_count"] > 0
        if is_individual_return and has_docs_but_no_w2:
            # Only flag if there are some documents but no W-2
            # (might be self-employed or retired)
            findings.append({
                    "severity": "info",
                    "category": "completeness",
                    "description": "No W-2 documents detected - verify if client has wage income",
                    "recommendation": "Confirm employment status with client",
                })

        # Check for duplicate documents
        filenames = [d["filename"] for d in context.get("documents", [])]
        duplicates = [f for f in filenames if filenames.count(f) > 1]
        if duplicates:
            findings.append({
                "severity": "warning",
                "category": "accuracy",
                "description": f"Possible duplicate documents detected: {', '.join(set(duplicates))}",
                "recommendation": "Review and remove duplicate documents",
            })

        return findings
