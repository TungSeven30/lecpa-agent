"""E2E test for scanned IRS notice with OCR."""

from pathlib import Path

import pytest


@pytest.mark.skipif(
    not Path("tests/golden/notice_scanned.pdf").exists(),
    reason="Scanned notice PDF not found in tests/golden/",
)
class TestNoticeOCRPipeline:
    """End-to-end tests for scanned notice OCR processing."""

    def test_notice_extraction_triggers_ocr(self, sample_notice_path: Path):
        """Test that scanned notice triggers OCR fallback."""
        from services.worker.tasks.extract import extract_pdf
        from services.worker.tasks.ocr import check_ocr_needed

        # Extract text (should be minimal for scanned doc)
        result = extract_pdf(str(sample_notice_path))

        # Check if OCR is needed (should be true for scanned)
        needs_ocr = check_ocr_needed(
            result["text"],
            sample_notice_path.stat().st_size,
            result["page_count"],
        )

        # Scanned document should need OCR
        assert needs_ocr, "Scanned document should trigger OCR fallback"

    def test_notice_ocr_extraction(self, sample_notice_path: Path):
        """Test OCR extraction on scanned notice."""
        from services.worker.tasks.ocr import ocr_document

        result = ocr_document(str(sample_notice_path))

        assert result["page_count"] >= 1
        assert len(result["text"]) > 0
        assert result["is_ocr"] is True
        assert "confidence" in result

    def test_notice_ocr_canonicalization(self, sample_notice_path: Path):
        """Test canonicalization of OCR text."""
        from services.worker.tasks.ocr import ocr_document
        from services.worker.tasks.canonicalize import canonicalize_document

        ocr_result = ocr_document(str(sample_notice_path))
        canonical_result = canonicalize_document(
            ocr_result["page_texts"],
            is_ocr=True,
        )

        assert len(canonical_result["text"]) > 0

    def test_notice_ocr_chunking_and_embedding(self, sample_notice_path: Path):
        """Test chunking and embedding of OCR text."""
        from services.worker.tasks.ocr import ocr_document
        from services.worker.tasks.canonicalize import canonicalize_document
        from services.worker.tasks.embed import chunk_and_embed

        ocr_result = ocr_document(str(sample_notice_path))
        canonical_result = canonicalize_document(
            ocr_result["page_texts"],
            is_ocr=True,
        )
        embed_result = chunk_and_embed(
            canonical_result["text"],
            canonical_result["page_texts"],
            is_ocr=True,
        )

        assert len(embed_result["chunks"]) > 0
        assert embed_result["model"] is not None
        assert embed_result["dimension"] > 0

        # Verify OCR flag is propagated
        for chunk in embed_result["chunks"]:
            assert chunk["is_ocr"] is True
            assert "embedding" in chunk
            assert len(chunk["embedding"]) == embed_result["dimension"]

    def test_notice_searchable_after_ocr_ingestion(
        self, sample_notice_path: Path, db_session
    ):
        """Test that OCR notice is searchable after full pipeline."""
        pytest.skip("Full ingestion test requires running worker")
