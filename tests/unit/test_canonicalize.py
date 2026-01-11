"""Unit tests for document canonicalization utilities.

These tests import from canonicalize_utils.py which contains pure functions
without any Celery dependencies, avoiding the import chain issues.
"""

import sys
from pathlib import Path

import pytest

# Add worker tasks directory to path for imports
_project_root = Path(__file__).parent.parent.parent
_worker_tasks_path = str(_project_root / "services" / "worker" / "tasks")
if _worker_tasks_path not in sys.path:
    sys.path.insert(0, _worker_tasks_path)

# Import from utils module (no Celery dependency!)
from canonicalize_utils import (
    collapse_whitespace,
    find_repeated_lines,
    normalize_ocr_artifacts,
    remove_headers_footers,
)


class TestCollapseWhitespace:
    """Tests for collapse_whitespace function."""

    def test_multiple_spaces(self):
        """Test collapsing multiple spaces."""
        text = "Hello    world"
        assert collapse_whitespace(text) == "Hello world"

    def test_multiple_newlines(self):
        """Test collapsing multiple newlines."""
        text = "Line 1\n\n\n\nLine 2"
        assert collapse_whitespace(text) == "Line 1\n\nLine 2"

    def test_trailing_whitespace(self):
        """Test removing trailing whitespace."""
        text = "Line 1   \nLine 2  "
        result = collapse_whitespace(text)
        assert result == "Line 1\nLine 2"

    def test_mixed_whitespace(self):
        """Test handling mixed whitespace."""
        text = "Word1   Word2\n\n\n\nWord3"
        result = collapse_whitespace(text)
        assert "   " not in result  # No triple spaces
        assert "\n\n\n" not in result  # No triple newlines


class TestFindRepeatedLines:
    """Tests for find_repeated_lines function."""

    def test_finds_headers(self):
        """Test finding repeated header lines."""
        pages = [
            "Company Name\nPage 1\nContent here",
            "Company Name\nPage 2\nMore content",
            "Company Name\nPage 3\nEven more",
            "Company Name\nPage 4\nFinal page",
        ]
        headers, footers = find_repeated_lines(pages)
        assert "Company Name" in headers

    def test_finds_footers(self):
        """Test finding repeated footer lines."""
        pages = [
            "Content\nConfidential - Do Not Copy",
            "More content\nConfidential - Do Not Copy",
            "Even more\nConfidential - Do Not Copy",
            "Last page\nConfidential - Do Not Copy",
        ]
        headers, footers = find_repeated_lines(pages)
        assert "Confidential - Do Not Copy" in footers

    def test_minimum_pages(self):
        """Test that too few pages returns empty sets."""
        pages = ["Page 1 header\nContent", "Page 2 header\nContent"]
        headers, footers = find_repeated_lines(pages)
        assert headers == set()
        assert footers == set()

    def test_threshold_filtering(self):
        """Test that threshold filters out non-repeated lines."""
        pages = [
            "Header\nContent 1",
            "Header\nContent 2",
            "Different\nContent 3",  # One page is different
            "Header\nContent 4",
        ]
        # With default 0.7 threshold (need 3 of 4 = 2.8, rounds to 2)
        headers, footers = find_repeated_lines(pages, threshold=0.7)
        assert "Header" in headers


class TestRemoveHeadersFooters:
    """Tests for remove_headers_footers function."""

    def test_removes_headers(self):
        """Test removing header lines."""
        text = "Company Name\nActual content here\nMore content"
        headers = {"Company Name"}
        result = remove_headers_footers(text, headers, set())
        assert "Company Name" not in result
        assert "Actual content here" in result

    def test_removes_footers(self):
        """Test removing footer lines."""
        text = "Content\nMore content\nPage 1 of 10"
        footers = {"Page 1 of 10"}
        result = remove_headers_footers(text, set(), footers)
        assert "Page 1 of 10" not in result
        assert "Content" in result

    def test_preserves_content(self):
        """Test that non-header/footer content is preserved."""
        text = "Header\nImportant content\nFooter"
        headers = {"Header"}
        footers = {"Footer"}
        result = remove_headers_footers(text, headers, footers)
        assert "Important content" in result


class TestNormalizeOCRArtifacts:
    """Tests for normalize_ocr_artifacts function."""

    def test_l_to_1_before_digit(self):
        """Test converting l to 1 before digits."""
        text = "Amount: $l234"
        result = normalize_ocr_artifacts(text)
        assert "1234" in result

    def test_pipe_to_1_before_digit(self):
        """Test converting | to 1 before digits."""
        text = "Value: |00"
        result = normalize_ocr_artifacts(text)
        assert "100" in result

    def test_zero_to_O_in_words(self):
        """Test converting 0 to O in word context."""
        text = "C0MPANY"
        result = normalize_ocr_artifacts(text)
        assert "COMPANY" in result

    def test_dollar_sign_spacing(self):
        """Test normalizing dollar sign spacing."""
        text = "Total: $ 500"
        result = normalize_ocr_artifacts(text)
        assert "$500" in result

    def test_comma_in_numbers(self):
        """Test normalizing comma spacing in numbers."""
        text = "Amount: 1 , 234"
        result = normalize_ocr_artifacts(text)
        assert "1,234" in result


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_document_processing(self):
        """Test processing a document through all steps."""
        pages = [
            "Bank Statement\nAccount: 12345\nBalance: $l,000.00\nBank Statement",
            "Bank Statement\nTransaction 1\nTransaction 2\nBank Statement",
            "Bank Statement\nTransaction 3\nFinal Balance: $2,500\nBank Statement",
        ]

        # Find headers/footers
        headers, footers = find_repeated_lines(pages)
        assert "Bank Statement" in headers or "Bank Statement" in footers

        # Process first page
        page_text = pages[0]
        cleaned = remove_headers_footers(page_text, headers, footers)
        cleaned = collapse_whitespace(cleaned)
        cleaned = normalize_ocr_artifacts(cleaned)

        # Should still have the account info
        assert "Account" in cleaned or "12345" in cleaned
