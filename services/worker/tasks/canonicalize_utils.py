"""Pure utility functions for document canonicalization.

These functions have no external dependencies and can be imported
safely without triggering the Celery app initialization.
"""

import re
from collections import Counter
from dataclasses import dataclass


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
    text = re.sub(r" +", " ", text)

    # Replace 3+ newlines with 2 newlines (preserve paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove trailing whitespace from lines
    lines = text.split("\n")
    lines = [line.rstrip() for line in lines]

    return "\n".join(lines)


def normalize_ocr_artifacts(text: str) -> str:
    """Normalize common OCR artifacts.

    Args:
        text: Input text potentially containing OCR errors

    Returns:
        Text with common OCR artifacts normalized
    """
    # Common OCR mistakes
    # l or | often misread as 1 in numeric contexts
    text = re.sub(r"[|l](?=\d)", "1", text)

    # O often misread as 0 in word contexts
    text = re.sub(r"(?<=[a-zA-Z])0(?=[a-zA-Z])", "O", text)

    # Fix common dollar sign issues
    text = re.sub(r"\$\s+(?=\d)", "$", text)

    # Normalize comma spacing in numbers
    text = re.sub(r"(?<=\d)\s*,\s*(?=\d{3})", ",", text)

    return text
