"""NAS folder structure parser.

Parses file paths on the NAS to extract client, case, and document information
based on the configured folder naming conventions.
"""

import re
from pathlib import Path

import structlog

from nas_sync.models import Config, ParsedPath

logger = structlog.get_logger()


class FolderParser:
    """Parse NAS folder structure to extract client/case/document info.

    The CPA firm's NAS follows this structure:
    - /volume1/LeCPA/ClientFiles/
        - 1xxx_ClientName/          (individual clients)
        - 2xxx_BusinessName/        (business entities)
            - 2024/                 (year folders → cases)
            - Permanent/            (evergreen documents)
            - Tax Notice/           (special tagged folder)
    """

    def __init__(self, config: Config):
        """Initialize the folder parser with configuration.

        Args:
            config: Full configuration object
        """
        self.config = config
        self._compile_patterns()

    def _glob_to_regex(self, pattern: str) -> str:
        """Convert a glob pattern to a regex pattern.

        Args:
            pattern: Glob pattern like '*.pdf' or '~$*'

        Returns:
            Regex pattern string
        """
        # Escape special regex characters first (except * and ?)
        # which we'll convert to regex equivalents
        special_chars = ".^$+{}[]|()\\"
        result = []
        for char in pattern:
            if char in special_chars:
                result.append(f"\\{char}")
            elif char == "*":
                result.append(".*")
            elif char == "?":
                result.append(".")
            else:
                result.append(char)
        return "".join(result)

    def _compile_patterns(self) -> None:
        """Compile regex patterns from configuration."""
        self.client_patterns: list[tuple[re.Pattern[str], str]] = [
            (re.compile(p.pattern), p.type) for p in self.config.parsing.client_patterns
        ]
        self.year_pattern = re.compile(self.config.parsing.year_pattern)
        self.skip_patterns: list[re.Pattern[str]] = [
            re.compile(self._glob_to_regex(p))
            for p in self.config.parsing.skip_patterns
        ]
        self.tag_patterns: list[tuple[re.Pattern[str], str]] = [
            (re.compile(p.pattern), p.tag) for p in self.config.parsing.document_tags
        ]
        self.special_folders = {
            f.folder: f for f in self.config.parsing.special_folders
        }

    def parse(self, full_path: str | Path) -> ParsedPath:
        """Parse a full NAS path into structured components.

        Args:
            full_path: Full path like /volume1/LeCPA/ClientFiles/1002_Name/2024/file.pdf

        Returns:
            ParsedPath with extracted information including:
            - client_code, client_name, client_type
            - year (if in a year folder)
            - folder_tag (if in a special folder)
            - is_permanent (if in Permanent folder)
            - detected_tags (auto-detected from filename)
        """
        path = Path(full_path)
        nas_root = Path(self.config.nas.root_path)

        # Get path relative to NAS root
        try:
            rel_path = path.relative_to(nas_root)
        except ValueError:
            return ParsedPath(
                relative_path=str(path),
                is_valid=False,
                skip_reason="Not under NAS root",
            )

        parts = rel_path.parts
        if len(parts) < 2:
            return ParsedPath(
                relative_path=str(rel_path),
                is_valid=False,
                skip_reason="Path too short (need client folder + file)",
            )

        # Check skip patterns against filename
        filename = path.name
        for pattern in self.skip_patterns:
            if pattern.match(filename):
                return ParsedPath(
                    relative_path=str(rel_path),
                    is_valid=False,
                    skip_reason=f"Matches skip pattern: {pattern.pattern}",
                )

        # Parse client folder (first component)
        client_folder = parts[0]
        client_code, client_name, client_type = self._parse_client_folder(client_folder)

        if not client_code:
            return ParsedPath(
                relative_path=str(rel_path),
                is_valid=False,
                skip_reason=f"Invalid client folder format: {client_folder}",
            )

        # Parse second level (year or special folder)
        year = None
        folder_tag = None
        is_permanent = False

        if len(parts) > 1:
            second_level = parts[1]
            year, folder_tag, is_permanent = self._parse_second_level(second_level)

        # Detect document tags from filename
        detected_tags = self._detect_tags(filename)

        # Path relative to client folder
        client_relative = str(Path(*parts[1:])) if len(parts) > 1 else ""

        logger.debug(
            "Parsed path",
            full_path=str(full_path),
            client_code=client_code,
            client_name=client_name,
            client_type=client_type,
            year=year,
            folder_tag=folder_tag,
            is_permanent=is_permanent,
            detected_tags=detected_tags,
        )

        return ParsedPath(
            client_code=client_code,
            client_name=client_name,
            client_type=client_type,
            year=year,
            folder_tag=folder_tag,
            is_permanent=is_permanent,
            relative_path=client_relative,
            detected_tags=detected_tags,
            is_valid=True,
        )

    def _parse_client_folder(
        self, folder_name: str
    ) -> tuple[str | None, str | None, str | None]:
        """Parse client folder name to extract code, name, and type.

        Args:
            folder_name: Folder name like "1002_Nguyen, Billy and Nguyen, Anny"

        Returns:
            Tuple of (client_code, client_name, client_type) or (None, None, None)
        """
        for pattern, client_type in self.client_patterns:
            match = pattern.match(folder_name)
            if match:
                return (
                    match.group("code"),
                    match.group("name"),
                    client_type,
                )
        return None, None, None

    def _parse_second_level(
        self, folder_name: str
    ) -> tuple[int | None, str | None, bool]:
        """Parse second level folder (year or special folder).

        Args:
            folder_name: Folder name like "2024" or "Permanent"

        Returns:
            Tuple of (year, folder_tag, is_permanent)
        """
        # Check if it's a year
        year_match = self.year_pattern.match(folder_name)
        if year_match:
            return int(year_match.group("year")), None, False

        # Check if it's a special folder
        if folder_name in self.special_folders:
            special = self.special_folders[folder_name]
            return None, special.tag, special.is_permanent

        return None, None, False

    def _detect_tags(self, filename: str) -> list[str]:
        """Detect document tags from filename.

        Args:
            filename: Name of the file

        Returns:
            List of detected tag strings
        """
        tags = []
        for pattern, tag in self.tag_patterns:
            if pattern.search(filename):
                tags.append(tag)
        return tags

    def is_lnk_file(self, path: str | Path) -> bool:
        """Check if a path is a Windows shortcut file.

        Args:
            path: File path to check

        Returns:
            True if the file is a .lnk shortcut
        """
        return Path(path).suffix.lower() == ".lnk"
