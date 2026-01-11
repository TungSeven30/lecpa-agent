"""Unit tests for ExtractionAgent."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Add paths for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "api"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages"))

from shared.models.agent_outputs import (
    ConfidenceLevel,
    ExtractionResult,
    W2Extraction,
    Form1099Extraction,
    K1Extraction,
)


class TestExtractionAgentParsing:
    """Tests for ExtractionAgent parsing utilities."""

    def test_parse_decimal_valid(self):
        """Test parsing valid decimal values."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        assert agent._parse_decimal(85000.00) == Decimal("85000.00")
        assert agent._parse_decimal("85000.00") == Decimal("85000.00")
        assert agent._parse_decimal(0) == Decimal("0")
        assert agent._parse_decimal("0.00") == Decimal("0.00")

    def test_parse_decimal_invalid(self):
        """Test parsing invalid decimal values."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        assert agent._parse_decimal(None) is None
        assert agent._parse_decimal("invalid") is None
        assert agent._parse_decimal("") is None

    def test_parse_confidence_valid(self):
        """Test parsing valid confidence levels."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        assert agent._parse_confidence("HIGH") == ConfidenceLevel.HIGH
        assert agent._parse_confidence("MEDIUM") == ConfidenceLevel.MEDIUM
        assert agent._parse_confidence("LOW") == ConfidenceLevel.LOW
        assert agent._parse_confidence("high") == ConfidenceLevel.HIGH  # Case insensitive

    def test_parse_confidence_invalid(self):
        """Test parsing invalid confidence levels defaults to MEDIUM."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        assert agent._parse_confidence("INVALID") == ConfidenceLevel.MEDIUM
        assert agent._parse_confidence("") == ConfidenceLevel.MEDIUM
        assert agent._parse_confidence(None) == ConfidenceLevel.MEDIUM

    def test_detect_document_type_from_tags(self):
        """Test document type detection from tags."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        # Tags are uppercased internally, so W2 should match
        assert agent._detect_document_type(["W2", "2024"]) == "W2"
        assert agent._detect_document_type(["1099-INT"]) == "1099"
        assert agent._detect_document_type(["1099-DIV", "income"]) == "1099"
        assert agent._detect_document_type(["K1", "partnership"]) == "K1"
        assert agent._detect_document_type(["other"]) == "UNKNOWN"
        assert agent._detect_document_type([]) == "UNKNOWN"

    def test_detect_document_type_empty_tags(self):
        """Test document type detection with empty tags list."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        # Empty list should return UNKNOWN (method expects list, not None)
        assert agent._detect_document_type([]) == "UNKNOWN"


class TestW2AnomalyDetection:
    """Tests for W-2 anomaly detection."""

    def test_detect_w2_anomalies_clean(self):
        """Test no anomalies for valid W-2 data."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        w2 = W2Extraction(
            employer_name="ACME Corp",
            employer_ein="12-3456789",
            wages=Decimal("85000.00"),
            federal_tax_withheld=Decimal("12000.00"),
            social_security_wages=Decimal("85000.00"),
            social_security_tax=Decimal("5270.00"),
            medicare_wages=Decimal("85000.00"),
            medicare_tax=Decimal("1232.50"),
            confidence=ConfidenceLevel.HIGH,
            anomalies=[],
        )

        anomalies = agent._detect_w2_anomalies(w2)
        assert len(anomalies) == 0

    def test_detect_w2_anomalies_negative_wages(self):
        """Test detection of negative wages."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        w2 = W2Extraction(
            employer_name="ACME Corp",
            wages=Decimal("-5000.00"),  # Negative!
            confidence=ConfidenceLevel.MEDIUM,
            anomalies=[],
        )

        anomalies = agent._detect_w2_anomalies(w2)
        assert any("negative" in a.lower() for a in anomalies)

    def test_detect_w2_anomalies_tax_exceeds_wages(self):
        """Test detection of tax exceeding wages."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        w2 = W2Extraction(
            employer_name="ACME Corp",
            wages=Decimal("50000.00"),
            federal_tax_withheld=Decimal("60000.00"),  # More than wages!
            confidence=ConfidenceLevel.MEDIUM,
            anomalies=[],
        )

        anomalies = agent._detect_w2_anomalies(w2)
        assert any("exceeds" in a.lower() or "greater" in a.lower() for a in anomalies)

    def test_detect_w2_anomalies_missing_employer(self):
        """Test detection of missing employer info."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        w2 = W2Extraction(
            employer_name=None,  # Missing!
            wages=Decimal("50000.00"),
            confidence=ConfidenceLevel.LOW,
            anomalies=[],
        )

        anomalies = agent._detect_w2_anomalies(w2)
        assert any("employer" in a.lower() or "missing" in a.lower() for a in anomalies)


class TestForm1099AnomalyDetection:
    """Tests for 1099 anomaly detection."""

    def test_detect_1099_anomalies_clean(self):
        """Test no anomalies for valid 1099 data."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        form_1099 = Form1099Extraction(
            form_type="1099-INT",
            payer_name="Big Bank Inc",
            payer_tin="98-7654321",
            amount=Decimal("1500.00"),
            confidence=ConfidenceLevel.HIGH,
            anomalies=[],
        )

        anomalies = agent._detect_1099_anomalies(form_1099)
        assert len(anomalies) == 0

    def test_detect_1099_anomalies_negative_amount(self):
        """Test detection of negative amount."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        form_1099 = Form1099Extraction(
            form_type="1099-INT",
            payer_name="Big Bank Inc",
            amount=Decimal("-500.00"),  # Negative!
            confidence=ConfidenceLevel.MEDIUM,
            anomalies=[],
        )

        anomalies = agent._detect_1099_anomalies(form_1099)
        assert any("negative" in a.lower() for a in anomalies)

    def test_detect_1099_anomalies_missing_payer(self):
        """Test detection of missing payer info."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        form_1099 = Form1099Extraction(
            form_type="1099-DIV",
            payer_name=None,  # Missing!
            amount=Decimal("2000.00"),
            confidence=ConfidenceLevel.LOW,
            anomalies=[],
        )

        anomalies = agent._detect_1099_anomalies(form_1099)
        assert any("payer" in a.lower() or "missing" in a.lower() for a in anomalies)


class TestK1AnomalyDetection:
    """Tests for K-1 anomaly detection."""

    def test_detect_k1_anomalies_clean(self):
        """Test no anomalies for valid K-1 data."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        k1 = K1Extraction(
            partnership_name="ABC Partnership",
            partnership_ein="11-2233445",
            ordinary_income=Decimal("25000.00"),
            confidence=ConfidenceLevel.HIGH,
            anomalies=[],
        )

        anomalies = agent._detect_k1_anomalies(k1)
        assert len(anomalies) == 0

    def test_detect_k1_anomalies_missing_ein(self):
        """Test detection of missing partnership EIN."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        k1 = K1Extraction(
            partnership_name="ABC Partnership",
            partnership_ein=None,  # Missing!
            ordinary_income=Decimal("25000.00"),
            confidence=ConfidenceLevel.MEDIUM,
            anomalies=[],
        )

        anomalies = agent._detect_k1_anomalies(k1)
        assert any("ein" in a.lower() or "missing" in a.lower() for a in anomalies)


class TestExtractionAgentIntegration:
    """Integration tests for ExtractionAgent with mocked LLM."""

    @pytest.mark.asyncio
    async def test_extract_w2_success(self):
        """Test successful W-2 extraction with mocked LLM response."""
        from services.agents.extraction_agent import ExtractionAgent

        mock_router = MagicMock()
        mock_router.generate = AsyncMock(return_value='''{
            "employer_name": "ACME Corporation",
            "employer_ein": "12-3456789",
            "employer_address": "123 Main St, Anytown, CA 90210",
            "employee_ssn_last4": "6789",
            "wages": 85000.00,
            "federal_tax_withheld": 12500.00,
            "social_security_wages": 85000.00,
            "social_security_tax": 5270.00,
            "medicare_wages": 85000.00,
            "medicare_tax": 1232.50,
            "state": "CA",
            "state_wages": 85000.00,
            "state_tax_withheld": 4250.00,
            "confidence": "HIGH",
            "anomalies": []
        }''')

        agent = ExtractionAgent(mock_router)
        doc_id = uuid4()

        # Mock the db session (not actually used in extract_w2)
        mock_db = AsyncMock()

        result = await agent.extract_w2(doc_id, "Sample W-2 document text", mock_db)

        assert result.document_type == "W2"
        assert result.w2 is not None
        assert result.w2.employer_name == "ACME Corporation"
        assert result.w2.wages == Decimal("85000.00")
        assert result.overall_confidence == ConfidenceLevel.HIGH
        assert result.needs_review is False

    @pytest.mark.asyncio
    async def test_extract_w2_json_parse_error(self):
        """Test W-2 extraction handles JSON parse errors gracefully."""
        from services.agents.extraction_agent import ExtractionAgent

        mock_router = MagicMock()
        mock_router.generate = AsyncMock(return_value="This is not valid JSON")

        agent = ExtractionAgent(mock_router)
        doc_id = uuid4()
        mock_db = AsyncMock()

        result = await agent.extract_w2(doc_id, "Sample W-2 document text", mock_db)

        # Should return a failed result with LOW confidence
        assert result.overall_confidence == ConfidenceLevel.LOW
        assert result.needs_review is True

    @pytest.mark.asyncio
    async def test_extract_1099_success(self):
        """Test successful 1099 extraction."""
        from services.agents.extraction_agent import ExtractionAgent

        mock_router = MagicMock()
        mock_router.generate = AsyncMock(return_value='''{
            "form_type": "1099-INT",
            "payer_name": "First National Bank",
            "payer_tin": "98-7654321",
            "recipient_ssn_last4": "4321",
            "amount": 1523.45,
            "federal_tax_withheld": 0.00,
            "state": null,
            "state_tax_withheld": null,
            "additional_fields": {
                "interest_income": 1523.45,
                "tax_exempt_interest": 0.00
            },
            "confidence": "HIGH",
            "anomalies": []
        }''')

        agent = ExtractionAgent(mock_router)
        doc_id = uuid4()
        mock_db = AsyncMock()

        result = await agent.extract_1099(doc_id, "Sample 1099-INT text", mock_db)

        assert result.document_type == "1099-INT"
        assert result.form_1099 is not None
        assert result.form_1099.payer_name == "First National Bank"
        assert result.form_1099.amount == Decimal("1523.45")

    @pytest.mark.asyncio
    async def test_extract_k1_success(self):
        """Test successful K-1 extraction."""
        from services.agents.extraction_agent import ExtractionAgent

        mock_router = MagicMock()
        mock_router.generate = AsyncMock(return_value='''{
            "partnership_name": "XYZ Investment Partners LP",
            "partnership_ein": "55-1234567",
            "partner_ssn_last4": "9876",
            "ordinary_income": 35000.00,
            "rental_income": null,
            "interest_income": 1200.00,
            "dividend_income": 2500.00,
            "capital_gain": 8000.00,
            "section_179": null,
            "other_income": {
                "guaranteed_payments": 12000.00
            },
            "confidence": "MEDIUM",
            "anomalies": []
        }''')

        agent = ExtractionAgent(mock_router)
        doc_id = uuid4()
        mock_db = AsyncMock()

        result = await agent.extract_k1(doc_id, "Sample K-1 text", mock_db)

        assert result.document_type == "K1"
        assert result.k1 is not None
        assert result.k1.partnership_name == "XYZ Investment Partners LP"
        assert result.k1.ordinary_income == Decimal("35000.00")
        assert result.k1.other_income.get("guaranteed_payments") == Decimal("12000.00")


class TestExtractionSummaryFormatting:
    """Tests for extraction summary formatting."""

    def test_format_extraction_summary_w2(self):
        """Test W-2 extraction summary formatting."""
        from services.agents.extraction_agent import ExtractionAgent

        agent = ExtractionAgent(MagicMock())

        w2 = W2Extraction(
            employer_name="Test Corp",
            employer_ein="12-3456789",
            wages=Decimal("75000.00"),
            federal_tax_withheld=Decimal("10000.00"),
            confidence=ConfidenceLevel.HIGH,
            anomalies=[],
        )

        result = ExtractionResult(
            document_id=uuid4(),
            document_type="W2",
            extracted_at="2024-01-15T10:00:00",
            w2=w2,
            overall_confidence=ConfidenceLevel.HIGH,
            anomalies=[],
            needs_review=False,
        )

        # Test that summary method exists and returns string
        summary = agent._format_extraction_summary(result, "w2_test.pdf")

        assert isinstance(summary, str)
        assert "W2" in summary or "W-2" in summary
        assert "Test Corp" in summary
