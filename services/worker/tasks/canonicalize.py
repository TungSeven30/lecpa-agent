"""Document canonicalization tasks.

Normalizes messy PDFs before chunking:
- Remove repeated headers/footers (bank statements, brokerage docs)
- Collapse excessive whitespace
- Preserve page boundaries as markers
- Normalize common OCR artifacts

The pure utility functions are in canonicalize_utils.py for easy testing.
"""

import structlog

from main import app

# Import pure functions from utils module (no Celery dependency)
from tasks.canonicalize_utils import (
    CanonicalizedDocument,
    collapse_whitespace,
    find_repeated_lines,
    normalize_ocr_artifacts,
    remove_headers_footers,
)

logger = structlog.get_logger()

# Re-export for backwards compatibility
__all__ = [
    "CanonicalizedDocument",
    "collapse_whitespace",
    "find_repeated_lines",
    "normalize_ocr_artifacts",
    "remove_headers_footers",
    "canonicalize_document",
]


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
