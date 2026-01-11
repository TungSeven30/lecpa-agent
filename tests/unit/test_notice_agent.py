"""Unit tests for NoticeAgent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Add paths for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "api"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages"))


class TestNoticeTypePrompts:
    """Tests for notice type-specific prompts."""

    def test_cp2000_prompt_exists(self):
        """Test CP2000 prompt is defined."""
        from services.agents.notice_agent import NoticeAgent

        assert "CP2000" in NoticeAgent.NOTICE_TYPE_PROMPTS
        prompt = NoticeAgent.NOTICE_TYPE_PROMPTS["CP2000"]
        assert "underreported" in prompt.lower()

    def test_cp501_prompt_exists(self):
        """Test CP501 prompt is defined."""
        from services.agents.notice_agent import NoticeAgent

        assert "CP501" in NoticeAgent.NOTICE_TYPE_PROMPTS
        prompt = NoticeAgent.NOTICE_TYPE_PROMPTS["CP501"]
        assert "balance" in prompt.lower() or "due" in prompt.lower()

    def test_cp504_prompt_exists(self):
        """Test CP504 prompt is defined."""
        from services.agents.notice_agent import NoticeAgent

        assert "CP504" in NoticeAgent.NOTICE_TYPE_PROMPTS
        prompt = NoticeAgent.NOTICE_TYPE_PROMPTS["CP504"]
        assert "levy" in prompt.lower()

    def test_lt11_prompt_exists(self):
        """Test LT11 prompt is defined."""
        from services.agents.notice_agent import NoticeAgent

        assert "LT11" in NoticeAgent.NOTICE_TYPE_PROMPTS
        prompt = NoticeAgent.NOTICE_TYPE_PROMPTS["LT11"]
        assert "levy" in prompt.lower() or "final" in prompt.lower()


class TestNoticeTypeInfo:
    """Tests for notice type information retrieval."""

    @patch('services.agents.notice_agent.get_template_renderer')
    def test_get_cp2000_info(self, mock_renderer):
        """Test getting CP2000 notice info."""
        mock_renderer.return_value = MagicMock()

        from services.agents.notice_agent import NoticeAgent

        agent = NoticeAgent(MagicMock())
        info = agent.get_notice_type_info("CP2000")

        assert info["name"] == "Underreported Income"
        assert info["severity"] == "medium"
        assert info["response_deadline_days"] == 30
        assert len(info["common_responses"]) > 0

    @patch('services.agents.notice_agent.get_template_renderer')
    def test_get_cp501_info(self, mock_renderer):
        """Test getting CP501 notice info."""
        mock_renderer.return_value = MagicMock()

        from services.agents.notice_agent import NoticeAgent

        agent = NoticeAgent(MagicMock())
        info = agent.get_notice_type_info("CP501")

        assert info["name"] == "Balance Due Reminder"
        assert info["severity"] == "low"
        assert info["response_deadline_days"] == 21

    @patch('services.agents.notice_agent.get_template_renderer')
    def test_get_cp504_info(self, mock_renderer):
        """Test getting CP504 (Intent to Levy) info."""
        mock_renderer.return_value = MagicMock()

        from services.agents.notice_agent import NoticeAgent

        agent = NoticeAgent(MagicMock())
        info = agent.get_notice_type_info("CP504")

        assert info["name"] == "Intent to Levy"
        assert info["severity"] == "high"
        assert "levy" in info["description"].lower()

    @patch('services.agents.notice_agent.get_template_renderer')
    def test_get_lt11_info(self, mock_renderer):
        """Test getting LT11 (Final Notice) info."""
        mock_renderer.return_value = MagicMock()

        from services.agents.notice_agent import NoticeAgent

        agent = NoticeAgent(MagicMock())
        info = agent.get_notice_type_info("LT11")

        assert info["name"] == "Final Notice - Intent to Levy"
        assert info["severity"] == "critical"

    @patch('services.agents.notice_agent.get_template_renderer')
    def test_get_unknown_notice_info(self, mock_renderer):
        """Test getting info for unknown notice type."""
        mock_renderer.return_value = MagicMock()

        from services.agents.notice_agent import NoticeAgent

        agent = NoticeAgent(MagicMock())
        info = agent.get_notice_type_info("UNKNOWN_TYPE")

        assert info["name"] == "IRS Notice"
        assert info["severity"] == "medium"
        assert info["response_deadline_days"] == 30


class TestNoticeAnalysis:
    """Tests for notice analysis with mocked LLM."""

    @pytest.mark.asyncio
    @patch('services.agents.notice_agent.get_template_renderer')
    async def test_analyze_notice_success(self, mock_renderer):
        """Test successful notice analysis."""
        mock_renderer.return_value = MagicMock()

        from services.agents.notice_agent import NoticeAgent

        mock_router = MagicMock()
        mock_router.generate = AsyncMock(return_value='''{
            "notice_type": "CP2000",
            "notice_summary": "IRS received 1099-INT income not reported on return",
            "issues": [
                {
                    "item": "Unreported interest income from First Bank",
                    "response": "Interest was reported on Schedule B, line 1",
                    "supporting_docs": ["1099-INT from First Bank", "Schedule B"]
                }
            ],
            "attachments_needed": [
                {"name": "1099-INT", "description": "Original 1099-INT from First Bank"}
            ],
            "missing_info": [],
            "deadline": "2024-03-15",
            "amount_due": 523.45,
            "confidence": "HIGH"
        }''')

        agent = NoticeAgent(mock_router)

        # Mock document and chunks retrieval
        mock_db = AsyncMock()
        mock_document = MagicMock()
        mock_document.id = uuid4()
        mock_db.get = AsyncMock(return_value=mock_document)

        # Mock the _get_document_text method
        with patch.object(agent, '_get_document_text', new_callable=AsyncMock) as mock_get_text:
            mock_get_text.return_value = "Sample IRS CP2000 notice text..."

            analysis = await agent.analyze_notice(mock_document.id, mock_db)

        assert analysis["notice_type"] == "CP2000"
        assert len(analysis["issues"]) == 1
        assert analysis["confidence"] == "HIGH"

    @pytest.mark.asyncio
    @patch('services.agents.notice_agent.get_template_renderer')
    async def test_analyze_notice_json_error(self, mock_renderer):
        """Test notice analysis handles JSON parse errors."""
        mock_renderer.return_value = MagicMock()

        from services.agents.notice_agent import NoticeAgent

        mock_router = MagicMock()
        mock_router.generate = AsyncMock(return_value="Invalid JSON response")

        agent = NoticeAgent(mock_router)

        mock_db = AsyncMock()
        mock_document = MagicMock()
        mock_document.id = uuid4()
        mock_db.get = AsyncMock(return_value=mock_document)

        with patch.object(agent, '_get_document_text', new_callable=AsyncMock) as mock_get_text:
            mock_get_text.return_value = "Sample notice text..."

            analysis = await agent.analyze_notice(mock_document.id, mock_db)

        # Should return a fallback result
        assert analysis["notice_type"] == "UNKNOWN"
        assert analysis["confidence"] == "LOW"


class TestNoticeResponseDrafting:
    """Tests for notice response letter drafting."""

    @pytest.mark.asyncio
    @patch('services.agents.notice_agent.get_template_renderer')
    async def test_draft_notice_response_success(self, mock_renderer):
        """Test successful notice response drafting."""
        mock_renderer_instance = MagicMock()
        mock_renderer_instance.render = MagicMock(return_value="Rendered letter content")
        mock_renderer.return_value = mock_renderer_instance

        from services.agents.notice_agent import NoticeAgent
        from shared.models.agent_outputs import NoticeResponse

        mock_router = MagicMock()
        # First call for analysis, second call for detailed response
        mock_router.generate = AsyncMock(side_effect=[
            '''{
                "notice_type": "CP2000",
                "notice_date": "January 15, 2024",
                "issues": [
                    {
                        "item": "Unreported 1099-INT income",
                        "response": "Income was reported on Schedule B",
                        "supporting_docs": ["1099-INT", "Tax return copy"]
                    }
                ],
                "attachments_needed": [
                    {"name": "1099-INT copy", "description": "Copy of original 1099-INT"}
                ],
                "missing_info": [],
                "confidence": "HIGH"
            }''',
            '''{
                "notice_type": "CP2000",
                "notice_date": "January 15, 2024",
                "issues": [
                    {
                        "item": "Unreported 1099-INT income from First Bank",
                        "response": "The interest income of $1,523.45 was properly reported.",
                        "supporting_docs": ["Original 1099-INT", "Copy of filed Schedule B"]
                    }
                ],
                "attachments_needed": [
                    {"name": "1099-INT", "description": "Original form showing the interest income"}
                ],
                "missing_info": [],
                "confidence": "HIGH"
            }'''
        ])

        agent = NoticeAgent(mock_router)

        mock_db = AsyncMock()
        mock_document = MagicMock()
        mock_document.id = uuid4()
        mock_db.get = AsyncMock(return_value=mock_document)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        case_id = uuid4()
        doc_id = uuid4()

        with patch.object(agent, '_get_document_text', new_callable=AsyncMock) as mock_get_text:
            mock_get_text.return_value = "CP2000 Notice - Tax Year 2023..."

            with patch('services.template_context.prepare_case_context', new_callable=AsyncMock) as mock_context:
                mock_context.return_value = {
                    "client_name": "John Doe",
                    "tax_year": "2023",
                    "case_type": "tax_return",
                }

                result = await agent.draft_notice_response(
                    case_id=case_id,
                    notice_document_id=doc_id,
                    db=mock_db,
                    client_name="John Doe",
                    ssn_last4="6789",
                )

        assert isinstance(result, NoticeResponse)
        assert result.notice_type == "CP2000"
        assert result.client_name == "John Doe"
        assert len(result.response_points) > 0
