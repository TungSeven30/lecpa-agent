"""Tests for NAS folder structure parser."""

import pytest

from nas_sync.config import get_default_config
from nas_sync.models import Config
from nas_sync.parser import FolderParser


@pytest.fixture
def config() -> Config:
    """Create a test configuration."""
    default = get_default_config()
    # Override NAS root for testing
    default["nas"]["root_path"] = "/volume1/LeCPA/ClientFiles"
    return Config(**default)


@pytest.fixture
def parser(config: Config) -> FolderParser:
    """Create a folder parser with test config."""
    return FolderParser(config)


class TestFolderParser:
    """Test suite for FolderParser."""

    def test_parse_individual_client_year_file(self, parser: FolderParser) -> None:
        """Test parsing path: individual client, year folder, document."""
        path = (
            "/volume1/LeCPA/ClientFiles"
            "/1002_Nguyen, Billy and Nguyen, Anny/2024/2024 W-2.pdf"
        )
        result = parser.parse(path)

        assert result.is_valid is True
        assert result.client_code == "1002"
        assert result.client_name == "Nguyen, Billy and Nguyen, Anny"
        assert result.client_type == "individual"
        assert result.year == 2024
        assert result.is_permanent is False
        assert result.folder_tag is None
        assert "W2" in result.detected_tags

    def test_parse_business_client_year_file(self, parser: FolderParser) -> None:
        """Test parsing path: business client, year folder, document."""
        path = (
            "/volume1/LeCPA/ClientFiles/2010_Sim Sim Realty LLC/2024/Annual Report.pdf"
        )
        result = parser.parse(path)

        assert result.is_valid is True
        assert result.client_code == "2010"
        assert result.client_name == "Sim Sim Realty LLC"
        assert result.client_type == "business"
        assert result.year == 2024
        assert result.is_permanent is False

    def test_parse_permanent_folder(self, parser: FolderParser) -> None:
        """Test parsing path in Permanent folder."""
        path = (
            "/volume1/LeCPA/ClientFiles"
            "/1001_Toh, Wei Ming/Permanent/S-Corp Election.pdf"
        )
        result = parser.parse(path)

        assert result.is_valid is True
        assert result.client_code == "1001"
        assert result.year is None
        assert result.is_permanent is True
        assert result.folder_tag == "permanent"

    def test_parse_tax_notice_folder(self, parser: FolderParser) -> None:
        """Test parsing path in Tax Notice folder."""
        path = (
            "/volume1/LeCPA/ClientFiles/1001_Toh, Wei Ming/Tax Notice/CP2000 Notice.pdf"
        )
        result = parser.parse(path)

        assert result.is_valid is True
        assert result.client_code == "1001"
        assert result.folder_tag == "tax_notice"
        assert result.is_permanent is False
        assert "IRS_NOTICE" in result.detected_tags

    def test_parse_k1_subfolder(self, parser: FolderParser) -> None:
        """Test parsing K-1 file in subfolder."""
        path = (
            "/volume1/LeCPA/ClientFiles"
            "/1002_Nguyen/2024/2024 K-1s/1. 2024 K1P_DBB Empire LLC.pdf"
        )
        result = parser.parse(path)

        assert result.is_valid is True
        assert result.client_code == "1002"
        assert result.year == 2024
        assert "K1" in result.detected_tags

    def test_skip_7z_archive(self, parser: FolderParser) -> None:
        """Test that .7z files are skipped."""
        path = "/volume1/LeCPA/ClientFiles/1001_Client/2024/D24_DB_backup.7z"
        result = parser.parse(path)

        assert result.is_valid is False
        assert "skip pattern" in (result.skip_reason or "").lower()

    def test_skip_zip_archive(self, parser: FolderParser) -> None:
        """Test that .zip files are skipped."""
        path = "/volume1/LeCPA/ClientFiles/1001_Client/2024/documents.zip"
        result = parser.parse(path)

        assert result.is_valid is False

    def test_skip_lnk_shortcut(self, parser: FolderParser) -> None:
        """Test that .lnk files are skipped (handled separately)."""
        path = "/volume1/LeCPA/ClientFiles/1001_Client/2010_Business.lnk"
        result = parser.parse(path)

        assert result.is_valid is False

    def test_skip_ds_store(self, parser: FolderParser) -> None:
        """Test that .DS_Store files are skipped."""
        path = "/volume1/LeCPA/ClientFiles/1001_Client/2024/.DS_Store"
        result = parser.parse(path)

        assert result.is_valid is False

    def test_skip_office_temp_file(self, parser: FolderParser) -> None:
        """Test that Office temp files (~$) are skipped."""
        path = "/volume1/LeCPA/ClientFiles/1001_Client/2024/~$Document.xlsx"
        result = parser.parse(path)

        assert result.is_valid is False

    def test_invalid_path_outside_root(self, parser: FolderParser) -> None:
        """Test that paths outside NAS root are invalid."""
        path = "/some/other/path/file.pdf"
        result = parser.parse(path)

        assert result.is_valid is False
        assert "NAS root" in (result.skip_reason or "")

    def test_invalid_client_folder_format(self, parser: FolderParser) -> None:
        """Test that invalid client folder names are rejected."""
        path = "/volume1/LeCPA/ClientFiles/BadFolderName/2024/file.pdf"
        result = parser.parse(path)

        assert result.is_valid is False
        assert "client folder" in (result.skip_reason or "").lower()

    def test_detect_multiple_tags(self, parser: FolderParser) -> None:
        """Test detection of multiple tags in filename."""
        # A file with both W-2 and 1099 in the name (unusual but test coverage)
        path = "/volume1/LeCPA/ClientFiles/1001_Client/2024/W-2 and 1099 Summary.pdf"
        result = parser.parse(path)

        assert result.is_valid is True
        assert "W2" in result.detected_tags
        assert "1099" in result.detected_tags

    def test_is_lnk_file(self, parser: FolderParser) -> None:
        """Test .lnk file detection."""
        assert parser.is_lnk_file("/path/to/file.lnk") is True
        assert parser.is_lnk_file("/path/to/file.LNK") is True
        assert parser.is_lnk_file("/path/to/file.pdf") is False
        assert parser.is_lnk_file("/path/to/file.lnk.pdf") is False

    def test_relative_path_extraction(self, parser: FolderParser) -> None:
        """Test that relative path is correctly extracted."""
        path = "/volume1/LeCPA/ClientFiles/1001_Client/2024/subfolder/file.pdf"
        result = parser.parse(path)

        assert result.is_valid is True
        assert result.relative_path == "2024/subfolder/file.pdf"


class TestClientPatterns:
    """Test client code pattern matching."""

    def test_individual_client_1000_series(self, parser: FolderParser) -> None:
        """Test individual client codes in 1000 series."""
        for code in ["1000", "1001", "1500", "1999"]:
            path = f"/volume1/LeCPA/ClientFiles/{code}_Test Client/2024/file.pdf"
            result = parser.parse(path)
            assert result.client_code == code
            assert result.client_type == "individual"

    def test_business_client_2000_series(self, parser: FolderParser) -> None:
        """Test business client codes in 2000 series."""
        for code in ["2000", "2001", "2500", "2999"]:
            path = f"/volume1/LeCPA/ClientFiles/{code}_Test Business LLC/2024/file.pdf"
            result = parser.parse(path)
            assert result.client_code == code
            assert result.client_type == "business"


class TestSpecialFolders:
    """Test special folder recognition."""

    @pytest.mark.parametrize(
        "folder,expected_tag,expected_permanent",
        [
            ("Permanent", "permanent", True),
            ("Tax Notice", "tax_notice", False),
            ("Tax Transcript", "transcript", False),
            ("Tax Emails", "emails", False),
            ("Invoice", "invoice", False),
        ],
    )
    def test_special_folder_tags(
        self,
        parser: FolderParser,
        folder: str,
        expected_tag: str,
        expected_permanent: bool,
    ) -> None:
        """Test that special folders get correct tags."""
        path = f"/volume1/LeCPA/ClientFiles/1001_Client/{folder}/file.pdf"
        result = parser.parse(path)

        assert result.is_valid is True
        assert result.folder_tag == expected_tag
        assert result.is_permanent is expected_permanent
