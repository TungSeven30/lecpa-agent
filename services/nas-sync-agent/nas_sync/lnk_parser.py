"""Windows .lnk shortcut file parser.

Parses Windows shortcuts to extract target paths, which are used to
establish relationships between individual clients and business entities.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger()


@dataclass
class ShortcutTarget:
    """Parsed shortcut target information."""

    target_path: str | None
    target_name: str | None
    is_valid: bool
    error: str | None = None


def parse_lnk_file(lnk_path: str | Path) -> ShortcutTarget:
    """Parse a Windows .lnk shortcut file to extract target path.

    This is a simplified parser for .lnk files commonly found on NAS.
    Handles the most common case of local file system targets.

    Windows .lnk files have a complex binary format. This parser looks
    for path strings embedded in the file content rather than fully
    parsing the structure.

    Args:
        lnk_path: Path to the .lnk file

    Returns:
        ShortcutTarget with extracted information
    """
    try:
        with open(lnk_path, "rb") as f:
            content = f.read()

        # LNK file header magic: 4C 00 00 00
        if content[:4] != b"\x4c\x00\x00\x00":
            return ShortcutTarget(
                target_path=None,
                target_name=None,
                is_valid=False,
                error="Not a valid LNK file (invalid magic bytes)",
            )

        # Try to find the target path in the file
        # LNK files often have paths as UTF-16LE encoded strings
        target_path = _extract_path_from_content(content)

        if target_path:
            target_name = Path(target_path).name
            logger.debug(
                "Parsed LNK file",
                lnk_path=str(lnk_path),
                target_path=target_path,
                target_name=target_name,
            )
            return ShortcutTarget(
                target_path=target_path,
                target_name=target_name,
                is_valid=True,
            )

        return ShortcutTarget(
            target_path=None,
            target_name=None,
            is_valid=False,
            error="Could not extract target path from LNK file",
        )

    except OSError as e:
        logger.error("Failed to read LNK file", path=str(lnk_path), error=str(e))
        return ShortcutTarget(
            target_path=None,
            target_name=None,
            is_valid=False,
            error=f"Failed to read file: {e}",
        )
    except Exception as e:
        logger.error("Failed to parse LNK file", path=str(lnk_path), error=str(e))
        return ShortcutTarget(
            target_path=None,
            target_name=None,
            is_valid=False,
            error=f"Parse error: {e}",
        )


def _extract_path_from_content(content: bytes) -> str | None:
    """Extract file system path from LNK file content.

    Args:
        content: Raw bytes of the LNK file

    Returns:
        Extracted path string or None if not found
    """
    # Try UTF-16LE decoding (common in Windows files)
    try:
        content_str = content.decode("utf-16-le", errors="ignore")
    except Exception:
        content_str = ""

    # Also try ASCII/UTF-8 for some path formats
    try:
        content_ascii = content.decode("utf-8", errors="ignore")
    except Exception:
        content_ascii = ""

    # Pattern for Windows local paths (e.g., C:\Users\...)
    local_pattern = r"[A-Za-z]:\\[^<>:\"|?*\x00-\x1f]+"
    # Pattern for UNC paths (e.g., \\server\share\...)
    unc_pattern = r"\\\\[^<>:\"|?*\x00-\x1f]+"

    # Search in UTF-16 decoded content
    matches = re.findall(local_pattern, content_str)
    if not matches:
        matches = re.findall(unc_pattern, content_str)

    # If no matches in UTF-16, try ASCII
    if not matches:
        matches = re.findall(local_pattern, content_ascii)
    if not matches:
        matches = re.findall(unc_pattern, content_ascii)

    if matches:
        # Take the longest match as it's likely the full path
        # Filter out very short matches (likely false positives)
        valid_matches = [m for m in matches if len(m) > 10]
        if valid_matches:
            return max(valid_matches, key=len)

    return None


def extract_client_code_from_lnk(
    lnk_path: str | Path,
    client_patterns: list[tuple[re.Pattern[str], str]],
) -> str | None:
    """Extract client code from a shortcut's target folder name.

    Used to establish relationships between clients. When an individual
    client folder contains a .lnk shortcut pointing to a business folder,
    we can extract the business's client code from the shortcut target.

    Args:
        lnk_path: Path to the .lnk file
        client_patterns: List of (compiled_pattern, client_type) tuples

    Returns:
        Client code if found and matches a pattern, None otherwise
    """
    target = parse_lnk_file(lnk_path)
    if not target.is_valid or not target.target_path:
        return None

    # Get the folder name from the target path
    target_folder_name = Path(target.target_path).name

    # Try to match against client patterns
    for pattern, _ in client_patterns:
        match = pattern.match(target_folder_name)
        if match:
            return match.group("code")

    return None


def find_relationship_from_lnk(
    lnk_path: str | Path,
    source_client_code: str,
    client_patterns: list[tuple[re.Pattern[str], str]],
) -> dict | None:
    """Extract relationship info from a .lnk file.

    When an individual's folder contains a shortcut to a business folder,
    this indicates an ownership relationship.

    Args:
        lnk_path: Path to the .lnk file
        source_client_code: Client code of the folder containing the .lnk
        client_patterns: List of (compiled_pattern, client_type) tuples

    Returns:
        Dictionary with relationship info or None if not applicable
        {
            "individual_code": "1001",
            "business_code": "2010",
            "source_path": "/path/to/shortcut.lnk"
        }
    """
    target_code = extract_client_code_from_lnk(lnk_path, client_patterns)
    if not target_code:
        return None

    # Determine which is individual and which is business based on code prefix
    # 1xxx = individual, 2xxx = business
    source_is_individual = source_client_code.startswith("1")
    target_is_business = target_code.startswith("2")

    if source_is_individual and target_is_business:
        return {
            "individual_code": source_client_code,
            "business_code": target_code,
            "source_path": str(lnk_path),
        }

    # Could also handle reverse case (business linking to individual)
    # but that's less common in the CPA's workflow
    return None
