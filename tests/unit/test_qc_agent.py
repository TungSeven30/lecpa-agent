"""Unit tests for QCAgent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Add paths for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "api"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages"))


class TestQCChecklists:
    """Tests for QC checklist content.

    Note: These tests access class attributes directly, so no instance needed.
    """

    def test_individual_checklist_has_required_sections(self):
        """Test individual checklist contains key sections."""
        from services.agents.qc_agent import QCAgent

        checklist = QCAgent.INDIVIDUAL_CHECKLIST

        # Should contain required document types
        assert "W-2" in checklist or "W2" in checklist
        assert "1099-INT" in checklist
        assert "1099-DIV" in checklist

        # Should contain verification sections
        assert "Income Verification" in checklist
        assert "Deductions" in checklist or "Credits" in checklist

    def test_business_checklist_has_required_sections(self):
        """Test business checklist contains key sections."""
        from services.agents.qc_agent import QCAgent

        checklist = QCAgent.BUSINESS_CHECKLIST

        # Should contain required document types
        assert "K-1" in checklist or "K1" in checklist
        assert "financial statements" in checklist.lower()
        assert "depreciation" in checklist.lower()

        # Should contain verification sections
        assert "Income Verification" in checklist
        assert "Deductions" in checklist


class TestAutomatedChecks:
    """Tests for automated QC checks."""

    @patch('services.agents.qc_agent.get_template_renderer')
    def test_no_findings_for_complete_case(self, mock_renderer):
        """Test no findings for a well-documented case."""
        mock_renderer.return_value = MagicMock()

        from services.agents.qc_agent import QCAgent

        agent = QCAgent(MagicMock())

        context = {
            "case_type": "tax_return",
            "document_count": 5,
            "documents": [
                {"filename": "w2_employer.pdf", "type": "W2"},
                {"filename": "1099_bank.pdf", "type": "1099-INT"},
                {"filename": "prior_year.pdf", "type": "prior_return"},
            ],
        }

        findings = agent._run_automated_checks([], context)

        # Should have no critical findings for a case with W-2
        assert not any(f["severity"] == "error" for f in findings)

    @patch('services.agents.qc_agent.get_template_renderer')
    def test_detects_missing_w2_for_individual(self, mock_renderer):
        """Test detection of missing W-2 for individual return."""
        mock_renderer.return_value = MagicMock()

        from services.agents.qc_agent import QCAgent

        agent = QCAgent(MagicMock())

        context = {
            "case_type": "tax_return",
            "document_count": 3,
            "documents": [
                {"filename": "1099_interest.pdf", "type": "1099-INT"},
                {"filename": "1099_div.pdf", "type": "1099-DIV"},
                {"filename": "misc_doc.pdf", "type": "other"},
            ],
        }

        findings = agent._run_automated_checks([], context)

        # Should flag missing W-2
        assert any("W-2" in f["description"] or "W2" in f["description"] for f in findings)

    @patch('services.agents.qc_agent.get_template_renderer')
    def test_detects_duplicate_documents(self, mock_renderer):
        """Test detection of duplicate document filenames."""
        mock_renderer.return_value = MagicMock()

        from services.agents.qc_agent import QCAgent

        agent = QCAgent(MagicMock())

        context = {
            "case_type": "tax_return",
            "document_count": 4,
            "documents": [
                {"filename": "w2_employer.pdf", "type": "W2"},
                {"filename": "w2_employer.pdf", "type": "W2"},  # Duplicate!
                {"filename": "1099_bank.pdf", "type": "1099-INT"},
                {"filename": "1099_bank.pdf", "type": "1099-INT"},  # Duplicate!
            ],
        }

        findings = agent._run_automated_checks([], context)

        # Should flag duplicates
        duplicate_findings = [f for f in findings if "duplicate" in f["description"].lower()]
        assert len(duplicate_findings) > 0

    @patch('services.agents.qc_agent.get_template_renderer')
    def test_no_w2_check_for_business_returns(self, mock_renderer):
        """Test W-2 check doesn't apply to business returns."""
        mock_renderer.return_value = MagicMock()

        from services.agents.qc_agent import QCAgent

        agent = QCAgent(MagicMock())

        context = {
            "case_type": "business_return",
            "document_count": 3,
            "documents": [
                {"filename": "financial_statements.pdf", "type": "financial"},
                {"filename": "k1_partner.pdf", "type": "K1"},
            ],
        }

        findings = agent._run_automated_checks([], context)

        # Should NOT flag missing W-2 for business return
        w2_findings = [f for f in findings if "W-2" in f["description"] or "W2" in f["description"]]
        assert len(w2_findings) == 0


class TestDocumentsSummary:
    """Tests for document summary building."""

    @patch('services.agents.qc_agent.get_template_renderer')
    def test_build_documents_summary_with_docs(self, mock_renderer):
        """Test building summary with documents."""
        mock_renderer.return_value = MagicMock()

        from services.agents.qc_agent import QCAgent

        agent = QCAgent(MagicMock())

        documents = [
            {"filename": "w2_acme.pdf", "tags": ["W2", "2024"], "processing_status": "ready"},
            {"filename": "1099_bank.pdf", "tags": ["1099-INT"], "processing_status": "ready"},
        ]

        summary = agent._build_documents_summary(documents)

        assert "w2_acme.pdf" in summary
        assert "1099_bank.pdf" in summary
        assert "W2" in summary
        assert "ready" in summary

    @patch('services.agents.qc_agent.get_template_renderer')
    def test_build_documents_summary_empty(self, mock_renderer):
        """Test building summary with no documents."""
        mock_renderer.return_value = MagicMock()

        from services.agents.qc_agent import QCAgent

        agent = QCAgent(MagicMock())

        summary = agent._build_documents_summary([])

        assert "No documents" in summary


class TestExtractionSummary:
    """Tests for extraction data summary building."""

    @patch('services.agents.qc_agent.get_template_renderer')
    def test_build_extraction_summary_with_data(self, mock_renderer):
        """Test building extraction summary with data."""
        mock_renderer.return_value = MagicMock()

        from services.agents.qc_agent import QCAgent

        agent = QCAgent(MagicMock())

        extractions = [
            {
                "title": "W-2 Extraction - ACME Corp",
                "content": "Employer: ACME Corp\nWages: $85,000.00",
                "created_at": "2024-01-15T10:00:00",
            },
        ]

        summary = agent._build_extraction_summary(extractions)

        assert "W-2 Extraction" in summary
        assert "ACME Corp" in summary

    @patch('services.agents.qc_agent.get_template_renderer')
    def test_build_extraction_summary_empty(self, mock_renderer):
        """Test building extraction summary with no data."""
        mock_renderer.return_value = MagicMock()

        from services.agents.qc_agent import QCAgent

        agent = QCAgent(MagicMock())

        summary = agent._build_extraction_summary([])

        assert "No extraction data" in summary


class TestQCMemoGeneration:
    """Tests for QC memo generation with mocked LLM."""

    @pytest.mark.asyncio
    @patch('services.agents.qc_agent.get_template_renderer')
    async def test_generate_qc_memo_success(self, mock_renderer):
        """Test successful QC memo generation."""
        mock_renderer_instance = MagicMock()
        mock_renderer_instance.render = MagicMock(return_value="Rendered QC memo content")
        mock_renderer.return_value = mock_renderer_instance

        from services.agents.qc_agent import QCAgent
        from shared.models.agent_outputs import QCReport

        mock_router = MagicMock()
        mock_router.generate = AsyncMock(return_value='''{
            "findings": [
                {
                    "severity": "warning",
                    "category": "completeness",
                    "description": "Missing 1099-DIV for reported dividend income",
                    "location": "Schedule B",
                    "recommendation": "Request 1099-DIV from client"
                }
            ],
            "missing_documents": ["1099-DIV"],
            "data_anomalies": [],
            "pass_status": true,
            "summary": "Minor documentation gap identified. Overall return appears accurate."
        }''')

        agent = QCAgent(mock_router)

        case_id = uuid4()
        mock_case = MagicMock()
        mock_case.id = case_id

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_case)
        mock_db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch('services.template_context.prepare_case_context', new_callable=AsyncMock) as mock_context:
            mock_context.return_value = {
                "client_name": "Jane Smith",
                "tax_year": "2023",
                "case_type": "tax_return",
                "document_count": 5,
                "documents": [
                    {"filename": "w2.pdf", "tags": ["W2"], "processing_status": "ready", "type": "W2"},
                ],
            }

            result = await agent.generate_qc_memo(case_id, mock_db)

        assert isinstance(result, QCReport)
        assert result.client_name == "Jane Smith"
        assert result.tax_year == 2023  # tax_year is stored as int
        assert len(result.findings) >= 1
        assert result.pass_status is True

    @pytest.mark.asyncio
    @patch('services.agents.qc_agent.get_template_renderer')
    async def test_generate_qc_memo_with_errors(self, mock_renderer):
        """Test QC memo generation with error findings."""
        mock_renderer_instance = MagicMock()
        mock_renderer_instance.render = MagicMock(return_value="Rendered QC memo")
        mock_renderer.return_value = mock_renderer_instance

        from services.agents.qc_agent import QCAgent
        from shared.models.agent_outputs import QCReport

        mock_router = MagicMock()
        mock_router.generate = AsyncMock(return_value='''{
            "findings": [
                {
                    "severity": "error",
                    "category": "accuracy",
                    "description": "W-2 wages do not match reported wages on return",
                    "location": "Form 1040, Line 1",
                    "recommendation": "Verify and correct wages amount"
                }
            ],
            "missing_documents": [],
            "data_anomalies": ["Wages mismatch: W-2 shows $85,000 but return shows $75,000"],
            "pass_status": false,
            "summary": "Critical error found. Return requires correction before filing."
        }''')

        agent = QCAgent(mock_router)

        case_id = uuid4()
        mock_case = MagicMock()
        mock_case.id = case_id

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_case)
        mock_db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch('services.template_context.prepare_case_context', new_callable=AsyncMock) as mock_context:
            mock_context.return_value = {
                "client_name": "Bob Jones",
                "tax_year": "2023",
                "case_type": "tax_return",
                "document_count": 3,
                "documents": [
                    {"filename": "w2.pdf", "tags": ["W2"], "processing_status": "ready", "type": "W2"},
                ],
            }

            result = await agent.generate_qc_memo(case_id, mock_db)

        assert isinstance(result, QCReport)
        assert result.pass_status is False  # Should fail due to error finding
        assert any(f.severity == "error" for f in result.findings)


class TestChecklistRunner:
    """Tests for checklist runner functionality."""

    @pytest.mark.asyncio
    @patch('services.agents.qc_agent.get_template_renderer')
    async def test_run_individual_checklist(self, mock_renderer):
        """Test running individual checklist."""
        mock_renderer.return_value = MagicMock()

        from services.agents.qc_agent import QCAgent

        mock_router = MagicMock()
        mock_router.generate = AsyncMock(return_value='''{
            "checklist_items": [
                {"item": "All W-2s present", "status": "PASS", "notes": "W-2 from ACME Corp on file"},
                {"item": "1099-INT for interest > $10", "status": "N/A", "notes": "No interest income reported"},
                {"item": "Prior year return", "status": "FAIL", "notes": "Prior year return not on file"}
            ],
            "overall_status": "FAIL",
            "critical_failures": ["Prior year return not on file"]
        }''')

        agent = QCAgent(mock_router)
        case_id = uuid4()

        mock_db = AsyncMock()

        with patch('services.template_context.prepare_case_context', new_callable=AsyncMock) as mock_context:
            mock_context.return_value = {
                "client_name": "Test Client",
                "tax_year": "2023",
                "case_type": "tax_return",
                "document_count": 2,
                "documents": [
                    {"filename": "w2.pdf", "tags": ["W2"], "processing_status": "ready"},
                ],
            }

            result = await agent.run_checklist(case_id, "individual", mock_db)

        assert result["overall_status"] == "FAIL"
        assert len(result["checklist_items"]) == 3
        assert len(result["critical_failures"]) == 1

    @pytest.mark.asyncio
    @patch('services.agents.qc_agent.get_template_renderer')
    async def test_run_checklist_invalid_type(self, mock_renderer):
        """Test running checklist with invalid type raises error."""
        mock_renderer.return_value = MagicMock()

        from services.agents.qc_agent import QCAgent

        agent = QCAgent(MagicMock())
        case_id = uuid4()
        mock_db = AsyncMock()

        # Mock prepare_case_context since it's called before validation
        with patch('services.template_context.prepare_case_context', new_callable=AsyncMock) as mock_context:
            mock_context.return_value = {
                "client_name": "Test Client",
                "case_type": "tax_return",
                "documents": [],
            }

            with pytest.raises(ValueError) as exc_info:
                await agent.run_checklist(case_id, "invalid_type", mock_db)

        assert "Unknown checklist type" in str(exc_info.value)
