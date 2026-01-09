"""Unit tests for SSN redaction utilities."""

import pytest

from shared.utils.redaction import (
    contains_ssn,
    extract_ssn_last4,
    mask_ssn,
    redact_ein_in_text,
    redact_ssn_in_text,
)


class TestMaskSSN:
    """Tests for mask_ssn function."""

    def test_mask_standard_format(self):
        """Test masking SSN in standard format."""
        assert mask_ssn("123-45-6789") == "XXX-XX-6789"

    def test_mask_no_dashes(self):
        """Test masking SSN without dashes."""
        assert mask_ssn("123456789") == "XXX-XX-6789"

    def test_mask_with_spaces(self):
        """Test masking SSN with spaces."""
        assert mask_ssn("123 45 6789") == "XXX-XX-6789"

    def test_mask_invalid_length(self):
        """Test masking invalid SSN."""
        assert mask_ssn("12345") == "XXX-XX-XXXX"
        assert mask_ssn("") == "XXX-XX-XXXX"


class TestExtractSSNLast4:
    """Tests for extract_ssn_last4 function."""

    def test_extract_valid_ssn(self):
        """Test extracting last 4 from valid SSN."""
        assert extract_ssn_last4("123-45-6789") == "6789"
        assert extract_ssn_last4("123456789") == "6789"

    def test_extract_invalid_ssn(self):
        """Test extracting from invalid SSN."""
        assert extract_ssn_last4("12345") is None
        assert extract_ssn_last4("") is None


class TestRedactSSNInText:
    """Tests for redact_ssn_in_text function."""

    def test_redact_single_ssn(self):
        """Test redacting a single SSN in text."""
        text = "SSN: 123-45-6789"
        result = redact_ssn_in_text(text)
        assert result == "SSN: XXX-XX-6789"

    def test_redact_multiple_ssns(self):
        """Test redacting multiple SSNs."""
        text = "SSN1: 123-45-6789, SSN2: 987-65-4321"
        result = redact_ssn_in_text(text)
        assert "XXX-XX-6789" in result
        assert "XXX-XX-4321" in result
        assert "123-45-6789" not in result

    def test_redact_no_ssn(self):
        """Test text without SSN."""
        text = "No SSN here"
        result = redact_ssn_in_text(text)
        assert result == text

    def test_redact_different_formats(self):
        """Test redacting SSNs in different formats."""
        text = "With dashes: 123-45-6789. Without: 123456789."
        result = redact_ssn_in_text(text)
        assert "123-45-6789" not in result
        assert "123456789" not in result


class TestContainsSSN:
    """Tests for contains_ssn function."""

    def test_contains_ssn_true(self):
        """Test detecting SSN in text."""
        assert contains_ssn("SSN: 123-45-6789") is True
        assert contains_ssn("123456789") is True

    def test_contains_ssn_false(self):
        """Test no SSN in text."""
        assert contains_ssn("No SSN here") is False
        assert contains_ssn("Phone: 123-456-7890") is False  # Wrong format


class TestRedactEIN:
    """Tests for EIN redaction."""

    def test_redact_ein(self):
        """Test redacting EIN in text."""
        text = "EIN: 12-3456789"
        result = redact_ein_in_text(text)
        assert "12-3456789" not in result
        assert "6789" in result  # Last 4 preserved
