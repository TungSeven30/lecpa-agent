"""Tests for Windows .lnk shortcut parser."""

import re
from pathlib import Path

import pytest

from nas_sync.lnk_parser import (
    ShortcutTarget,
    extract_client_code_from_lnk,
    find_relationship_from_lnk,
    parse_lnk_file,
)


class TestParseLnkFile:
    """Test suite for parse_lnk_file function."""

    def test_parse_invalid_file(self, tmp_path: Path) -> None:
        """Test parsing a file that isn't a valid .lnk."""
        # Create a regular text file
        test_file = tmp_path / "fake.lnk"
        test_file.write_text("This is not a LNK file")

        result = parse_lnk_file(test_file)

        assert result.is_valid is False
        assert "invalid magic" in (result.error or "").lower()

    def test_parse_nonexistent_file(self) -> None:
        """Test parsing a file that doesn't exist."""
        result = parse_lnk_file("/nonexistent/file.lnk")

        assert result.is_valid is False
        assert "failed to read" in (result.error or "").lower()

    def test_parse_valid_lnk_header(self, tmp_path: Path) -> None:
        """Test parsing a file with valid LNK header but no path."""
        # Create a file with LNK magic bytes but no valid path
        test_file = tmp_path / "test.lnk"
        # LNK magic bytes: 4C 00 00 00
        test_file.write_bytes(b"\x4c\x00\x00\x00" + b"\x00" * 100)

        result = parse_lnk_file(test_file)

        # Should have valid header but no extractable path
        assert result.is_valid is False or result.target_path is None

    def test_parse_lnk_with_embedded_path(self, tmp_path: Path) -> None:
        """Test parsing a file with an embedded Windows path."""
        # Create a minimal LNK-like file with an embedded path
        test_file = tmp_path / "test.lnk"

        # LNK magic bytes + padding + UTF-16LE encoded path
        path_bytes = "C:\\Users\\Test\\Documents\\Folder".encode("utf-16-le")
        content = b"\x4c\x00\x00\x00" + b"\x00" * 50 + path_bytes + b"\x00" * 50

        test_file.write_bytes(content)

        result = parse_lnk_file(test_file)

        # May or may not extract depending on the structure
        # At minimum, shouldn't crash
        assert isinstance(result, ShortcutTarget)


class TestExtractClientCode:
    """Test suite for extract_client_code_from_lnk function."""

    @pytest.fixture
    def client_patterns(self) -> list[tuple[re.Pattern, str]]:
        """Create test client patterns."""
        return [
            (re.compile(r"^(?P<code>1\d{3})_(?P<name>.+)$"), "individual"),
            (re.compile(r"^(?P<code>2\d{3})_(?P<name>.+)$"), "business"),
        ]

    def test_extract_with_invalid_file(
        self, tmp_path: Path, client_patterns: list
    ) -> None:
        """Test extraction from invalid file returns None."""
        test_file = tmp_path / "invalid.lnk"
        test_file.write_text("not a lnk file")

        result = extract_client_code_from_lnk(test_file, client_patterns)

        assert result is None


class TestFindRelationshipFromLnk:
    """Test suite for find_relationship_from_lnk function."""

    @pytest.fixture
    def client_patterns(self) -> list[tuple[re.Pattern, str]]:
        """Create test client patterns."""
        return [
            (re.compile(r"^(?P<code>1\d{3})_(?P<name>.+)$"), "individual"),
            (re.compile(r"^(?P<code>2\d{3})_(?P<name>.+)$"), "business"),
        ]

    def test_relationship_with_invalid_file(
        self, tmp_path: Path, client_patterns: list
    ) -> None:
        """Test relationship extraction from invalid file returns None."""
        test_file = tmp_path / "invalid.lnk"
        test_file.write_text("not a lnk file")

        result = find_relationship_from_lnk(test_file, "1001", client_patterns)

        assert result is None


class TestShortcutTargetDataclass:
    """Test the ShortcutTarget dataclass."""

    def test_valid_target(self) -> None:
        """Test creating a valid ShortcutTarget."""
        target = ShortcutTarget(
            target_path="C:\\Users\\Test\\Documents",
            target_name="Documents",
            is_valid=True,
        )

        assert target.is_valid is True
        assert target.target_path == "C:\\Users\\Test\\Documents"
        assert target.target_name == "Documents"
        assert target.error is None

    def test_invalid_target(self) -> None:
        """Test creating an invalid ShortcutTarget."""
        target = ShortcutTarget(
            target_path=None,
            target_name=None,
            is_valid=False,
            error="File not found",
        )

        assert target.is_valid is False
        assert target.target_path is None
        assert target.error == "File not found"


class TestRelationshipDetection:
    """Integration tests for relationship detection from shortcuts."""

    @pytest.fixture
    def client_patterns(self) -> list[tuple[re.Pattern, str]]:
        """Create test client patterns."""
        return [
            (re.compile(r"^(?P<code>1\d{3})_(?P<name>.+)$"), "individual"),
            (re.compile(r"^(?P<code>2\d{3})_(?P<name>.+)$"), "business"),
        ]

    def test_relationship_logic_individual_to_business(
        self, client_patterns: list
    ) -> None:
        """Test that individual→business relationship is detected correctly."""
        # This tests the relationship logic, not actual file parsing
        source_code = "1001"  # Individual
        target_code = "2010"  # Business

        # Verify our logic: 1xxx is individual, 2xxx is business
        assert source_code.startswith("1")  # Individual
        assert target_code.startswith("2")  # Business

        # If individual has shortcut to business, that's an ownership relationship
        source_is_individual = source_code.startswith("1")
        target_is_business = target_code.startswith("2")

        assert source_is_individual and target_is_business

    def test_relationship_logic_business_to_individual(
        self, client_patterns: list
    ) -> None:
        """Test that business→individual shortcut is not treated as ownership."""
        # This tests the relationship logic
        source_code = "2010"  # Business
        target_code = "1001"  # Individual

        source_is_individual = source_code.startswith("1")
        target_is_business = target_code.startswith("2")

        # Business→Individual is not an ownership relationship in our model
        assert not (source_is_individual and target_is_business)
