"""E2E test for 1099 document pipeline."""

from pathlib import Path

import pytest


@pytest.mark.skipif(
    not Path("tests/golden/1099_sample.pdf").exists(),
    reason="1099 sample PDF not found in tests/golden/",
)
class Test1099Pipeline:
    """End-to-end tests for 1099 document processing."""

    def test_1099_extraction(self, sample_1099_path: Path):
        """Test that 1099 text extraction works."""
        from services.worker.tasks.extract import extract_pdf

        result = extract_pdf(str(sample_1099_path))

        assert result["page_count"] >= 1
        assert len(result["text"]) > 0
        assert len(result["page_texts"]) == result["page_count"]

    def test_1099_canonicalization(self, sample_1099_path: Path):
        """Test 1099 canonicalization."""
        from services.worker.tasks.extract import extract_pdf
        from services.worker.tasks.canonicalize import canonicalize_document

        extract_result = extract_pdf(str(sample_1099_path))
        canonical_result = canonicalize_document(
            extract_result["page_texts"],
            is_ocr=False,
        )

        assert len(canonical_result["text"]) > 0
        assert len(canonical_result["page_texts"]) == extract_result["page_count"]

    def test_1099_chunking_and_embedding(self, sample_1099_path: Path):
        """Test 1099 chunking and embedding."""
        from services.worker.tasks.extract import extract_pdf
        from services.worker.tasks.canonicalize import canonicalize_document
        from services.worker.tasks.embed import chunk_and_embed

        extract_result = extract_pdf(str(sample_1099_path))
        canonical_result = canonicalize_document(
            extract_result["page_texts"],
            is_ocr=False,
        )
        embed_result = chunk_and_embed(
            canonical_result["text"],
            canonical_result["page_texts"],
            is_ocr=False,
        )

        assert len(embed_result["chunks"]) > 0
        assert embed_result["model"] is not None
        assert embed_result["dimension"] > 0

        for chunk in embed_result["chunks"]:
            assert "embedding" in chunk
            assert len(chunk["embedding"]) == embed_result["dimension"]

    def test_1099_searchable_after_ingestion(self, sample_1099_path: Path, db_session):
        """Test that 1099 is searchable after full pipeline."""
        pytest.skip("Full ingestion test requires running worker")
