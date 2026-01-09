"""Document canonicalization tasks.

Normalizes messy PDFs before chunking:
- Remove repeated headers/footers (bank statements, brokerage docs)
- Collapse excessive whitespace
- Preserve page boundaries as markers
- Normalize common OCR artifacts
"""

import re
from collections import Counter
from dataclasses import dataclass

import structlog

from main import app

logger = structlog.get_logger()


@dataclass
class CanonicalizedDocument:
    """Result from document canonicalization."""

    text: str
    page_texts: list[str]
    removed_headers: list[str]
    removed_footers: list[str]


def find_repeated_lines(page_texts: list[str], threshold: float = 0.7) -> tuple[set[str], set[str]]:
    """Find lines that repeat across pages (likely headers/footers).

    Args:
        page_texts: List of text per page
        threshold: Fraction of pages a line must appear on to be considered repeated

    Returns:
        Tuple of (header candidates, footer candidates)
    """
    if len(page_texts) < 3:
        return set(), set()

    min_occurrences = int(len(page_texts) * threshold)

    # Get first and last few lines of each page
    first_lines: list[str] = []
    last_lines: list[str] = []

    for page_text in page_texts:
        lines = [l.strip() for l in page_text.split("\n") if l.strip()]
        if lines:
            # First 3 lines as potential headers
            first_lines.extend(lines[:3])
            # Last 3 lines as potential footers
            last_lines.extend(lines[-3:])

    # Count occurrences
    first_counts = Counter(first_lines)
    last_counts = Counter(last_lines)

    # Filter by threshold
    headers = {line for line, count in first_counts.items() if count >= min_occurrences and len(line) > 5}
    footers = {line for line, count in last_counts.items() if count >= min_occurrences and len(line) > 5}

    return headers, footers


def remove_headers_footers(text: str, headers: set[str], footers: set[str]) -> str:
    """Remove identified headers and footers from text.

    Args:
        text: Page text
        headers: Set of header lines to remove
        footers: Set of footer lines to remove

    Returns:
        Cleaned text
    """
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped and stripped not in headers and stripped not in footers:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def collapse_whitespace(text: str) -> str:
    """Collapse excessive whitespace while preserving structure.

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace
    """
    # Replace multiple spaces with single space
    text = re.sub(r"[ \t]+", " ", text)

    # Replace 3+ consecutive newlines with 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove trailing whitespace from lines
    lines = [line.rstrip() for line in text.split("\n")]

    return "\n".join(lines)


def normalize_ocr_artifacts(text: str) -> str:
    """Normalize common OCR artifacts.

    Args:
        text: Input text

    Returns:
        Text with normalized artifacts
    """
    # Common OCR substitutions
    replacements = [
        (r"\bl\b(?=\d)", "1"),  # Lowercase L before numbers -> 1
        (r"(?<=\d)O(?=\d)", "0"),  # Capital O between numbers -> 0
        (r"(?<=\d)l(?=\d)", "1"),  # Lowercase L between numbers -> 1
        (r"\bll\b", "11"),  # Double L -> 11
        (r"(?<=[A-Z])0(?=[A-Z])", "O"),  # Zero between caps -> O
    ]

    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)

    return text


@app.task(bind=True, name="tasks.canonicalize.canonicalize_document")
def canonicalize_document(self, page_texts: list[str], is_ocr: bool = False) -> dict:
    """Canonicalize document text.

    Args:
        page_texts: List of text per page
        is_ocr: Whether the text came from OCR

    Returns:
        Dict with canonicalized text and metadata
    """
    logger.info(
        "Canonicalizing document",
        page_count=len(page_texts),
        is_ocr=is_ocr,
    )

    # Find repeated headers/footers
    headers, footers = find_repeated_lines(page_texts)

    logger.debug(
        "Found repeated lines",
        header_count=len(headers),
        footer_count=len(footers),
    )

    # Process each page
    cleaned_pages = []
    for i, page_text in enumerate(page_texts):
        # Remove headers/footers
        cleaned = remove_headers_footers(page_text, headers, footers)

        # Collapse whitespace
        cleaned = collapse_whitespace(cleaned)

        # Normalize OCR artifacts if needed
        if is_ocr:
            cleaned = normalize_ocr_artifacts(cleaned)

        # Add page marker
        cleaned = f"[PAGE {i + 1}]\n{cleaned}"
        cleaned_pages.append(cleaned)

    # Combine pages
    full_text = "\n\n".join(cleaned_pages)

    return {
        "text": full_text,
        "page_texts": cleaned_pages,
        "removed_headers": list(headers),
        "removed_footers": list(footers),
    }
