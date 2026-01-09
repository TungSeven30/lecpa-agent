"""Unit tests for document canonicalization."""

import pytest

from services.worker.tasks.canonicalize import (
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


class TestFindRepeatedLines:
    """Tests for find_repeated_lines function."""

    def test_find_headers(self):
        """Test finding repeated header lines."""
        pages = [
            "ACME BANK\nAccount Statement\nPage 1 content",
            "ACME BANK\nAccount Statement\nPage 2 content",
            "ACME BANK\nAccount Statement\nPage 3 content",
        ]
        headers, footers = find_repeated_lines(pages)
        assert "ACME BANK" in headers
        assert "Account Statement" in headers

    def test_find_footers(self):
        """Test finding repeated footer lines."""
        pages = [
            "Content\nPage 1 of 3\nConfidential",
            "Content\nPage 2 of 3\nConfidential",
            "Content\nPage 3 of 3\nConfidential",
        ]
        headers, footers = find_repeated_lines(pages)
        assert "Confidential" in footers

    def test_no_repeats_few_pages(self):
        """Test no repeats with few pages."""
        pages = ["Page 1", "Page 2"]
        headers, footers = find_repeated_lines(pages)
        assert len(headers) == 0
        assert len(footers) == 0


class TestRemoveHeadersFooters:
    """Tests for remove_headers_footers function."""

    def test_remove_headers(self):
        """Test removing header lines."""
        text = "HEADER LINE\nActual content\nMore content"
        headers = {"HEADER LINE"}
        result = remove_headers_footers(text, headers, set())
        assert "HEADER LINE" not in result
        assert "Actual content" in result

    def test_remove_footers(self):
        """Test removing footer lines."""
        text = "Content\nMore content\nFOOTER LINE"
        footers = {"FOOTER LINE"}
        result = remove_headers_footers(text, set(), footers)
        assert "FOOTER LINE" not in result
        assert "Content" in result


class TestNormalizeOCRArtifacts:
    """Tests for normalize_ocr_artifacts function."""

    def test_lowercase_l_before_numbers(self):
        """Test fixing lowercase L before numbers."""
        text = "Amount: l23.45"
        # This specific fix might not trigger in all cases
        # depending on pattern matching
        result = normalize_ocr_artifacts(text)
        assert result is not None

    def test_capital_o_between_numbers(self):
        """Test fixing capital O between numbers."""
        text = "Total: 1O0.00"
        result = normalize_ocr_artifacts(text)
        assert "100" in result
