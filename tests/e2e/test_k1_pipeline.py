"""E2E test for K-1 document pipeline."""

from pathlib import Path

import pytest


@pytest.mark.skipif(
    not Path("tests/golden/k1_sample.pdf").exists(),
    reason="K-1 sample PDF not found in tests/golden/",
)
class TestK1Pipeline:
    """End-to-end tests for K-1 document processing."""

    def test_k1_extraction(self, sample_k1_path: Path):
        """Test that K-1 text extraction works."""
        from services.worker.tasks.extract import extract_pdf

        result = extract_pdf(str(sample_k1_path))

        assert result["page_count"] >= 1
        assert len(result["text"]) > 0
        assert len(result["page_texts"]) == result["page_count"]

    def test_k1_canonicalization(self, sample_k1_path: Path):
        """Test K-1 canonicalization."""
        from services.worker.tasks.extract import extract_pdf
        from services.worker.tasks.canonicalize import canonicalize_document

        extract_result = extract_pdf(str(sample_k1_path))
        canonical_result = canonicalize_document(
            extract_result["page_texts"],
            is_ocr=False,
        )

        assert len(canonical_result["text"]) > 0
        assert len(canonical_result["page_texts"]) == extract_result["page_count"]

    def test_k1_chunking_and_embedding(self, sample_k1_path: Path):
        """Test K-1 chunking and embedding."""
        from services.worker.tasks.extract import extract_pdf
        from services.worker.tasks.canonicalize import canonicalize_document
        from services.worker.tasks.embed import chunk_and_embed

        extract_result = extract_pdf(str(sample_k1_path))
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

    def test_k1_searchable_after_ingestion(self, sample_k1_path: Path, db_session):
        """Test that K-1 is searchable after full pipeline."""
        pytest.skip("Full ingestion test requires running worker")
